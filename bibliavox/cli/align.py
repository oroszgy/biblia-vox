import json
import time
import statistics
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from bibliavox.align.evaluate import (
    build_comparison_table,
    compute_timestamp_accuracy,
    compute_wer,
    load_cached_result,
    save_cached_result,
    save_evaluation_report,
)
from bibliavox.align.forced import align_chapter, save_forced_alignment
from bibliavox.align.match import match_verses
from bibliavox.align.transcribe import transcribe_audio
from bibliavox.align.vibevoice import vibevoice_asr_match, vibevoice_direct
from bibliavox.config import get_settings

app = typer.Typer(help="Alignment commands for text to audio synchronization.")
console = Console()


@app.command("transcribe")
def transcribe_command(
    book: str = typer.Option(..., help="USX book code (e.g. GEN)"),
    chapter: int = typer.Option(..., help="Chapter number"),
    model: str = typer.Option(
        None, help="Specific model ID to run (defaults to all in gauntlet)"
    ),
) -> None:
    """Transcribe audio and generate word-level timestamps."""
    settings = get_settings()

    audio_path = settings.data_dir / "prepared" / "audio" / book / f"{chapter:03d}.wav"
    if not audio_path.exists():
        console.print(f"[red]Error: Audio file not found at {audio_path}[/red]")
        raise typer.Exit(1)

    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]
        if not models_to_run:
            console.print(
                f"[red]Error: Model {model} not found in gauntlet configuration[/red]"
            )
            raise typer.Exit(1)

    align_dir = settings.data_dir / "processed" / "align"
    align_dir.mkdir(parents=True, exist_ok=True)

    for model_config in models_to_run:
        console.print(f"[cyan]Transcribing with {model_config.id}...[/cyan]")
        try:
            words = transcribe_audio(audio_path, model_config, settings.models_dir)

            # Sanitize model name for filesystem
            model_safe_name = model_config.id.replace("/", "_")
            out_path = (
                align_dir / f"{book}_{chapter:03d}_{model_safe_name}_transcript.json"
            )

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(words, f, ensure_ascii=False, indent=2)

            console.print(f"[green]Saved {len(words)} words to {out_path}[/green]")
        except Exception as e:
            console.print(f"[red]Transcription failed for {model_config.id}: {e}[/red]")
            raise typer.Exit(1)


@app.command("match")
def match_command(
    book: str = typer.Option(..., help="USX book code (e.g. GEN)"),
    chapter: int = typer.Option(..., help="Chapter number"),
    model: str = typer.Option(
        None, help="Specific model ID to match (defaults to all in gauntlet)"
    ),
) -> None:
    """Match transcribed words to Bible verse canonical text."""
    settings = get_settings()

    # Read MEK text (primary canonical source)
    mek_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not mek_path.exists():
        console.print(f"[red]Error: Text corpus not found at {mek_path}[/red]")
        raise typer.Exit(1)

    verses = []
    with open(mek_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            if verse.get("book") == book and verse.get("chapter") == chapter:
                verses.append(
                    {"verse_id": str(verse.get("verse")), "text": verse.get("text", "")}
                )

    if not verses:
        console.print(
            f"[red]Error: No verses found for {book} {chapter} in MEK corpus[/red]"
        )
        raise typer.Exit(1)

    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]

    align_dir = settings.data_dir / "processed" / "align"

    for model_config in models_to_run:
        model_safe_name = model_config.id.replace("/", "_")
        transcript_path = (
            align_dir / f"{book}_{chapter:03d}_{model_safe_name}_transcript.json"
        )

        if not transcript_path.exists():
            console.print(
                f"[yellow]Skipping {model_config.id}: transcript not found[/yellow]"
            )
            continue

        with open(transcript_path, "r", encoding="utf-8") as f:
            word_transcripts = json.load(f)

        console.print(f"[cyan]Matching verses for {model_config.id}...[/cyan]")
        matched_verses = match_verses(verses, word_transcripts)

        out_path = align_dir / f"{book}_{chapter:03d}_{model_safe_name}_verses.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(matched_verses, f, ensure_ascii=False, indent=2)

        console.print(
            f"[green]Saved {len(matched_verses)} matched verses to {out_path}[/green]"
        )


@app.command("forced")
def forced_command(
    book: str = typer.Option(..., help="USX book code (e.g. GEN)"),
    chapter: int = typer.Option(..., help="Chapter number"),
    use_star: bool = typer.Option(
        True, help="Use <star> token for mismatch absorption"
    ),
) -> None:
    """Run MMS_FA forced alignment for a chapter."""
    settings = get_settings()

    audio_path = settings.data_dir / "prepared" / "audio" / book / f"{chapter:03d}.wav"
    if not audio_path.exists():
        console.print(f"[red]Error: Audio file not found at {audio_path}[/red]")
        raise typer.Exit(1)

    # Load verses from MEK JSONL corpus (D-04)
    mek_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not mek_path.exists():
        console.print(f"[red]Error: Text corpus not found at {mek_path}[/red]")
        raise typer.Exit(1)

    verses = []
    with open(mek_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            if verse.get("book") == book and verse.get("chapter") == chapter:
                verses.append(
                    {"verse_id": str(verse.get("verse")), "text": verse.get("text", "")}
                )

    if not verses:
        console.print(
            f"[red]Error: No verses found for {book} {chapter} in MEK corpus[/red]"
        )
        raise typer.Exit(1)

    console.print(
        f"[cyan]Running MMS_FA forced alignment for {book} {chapter}...[/cyan]"
    )
    console.print(f"[cyan]  Verses: {len(verses)}, Audio: {audio_path}[/cyan]")

    try:
        results = align_chapter(audio_path, verses, device="cuda", use_star=use_star)
    except Exception as e:
        console.print(f"[red]Forced alignment failed: {e}[/red]")
        raise typer.Exit(1)

    # Save results to data/aligned/mms_fa/{book}/
    aligned_dir = settings.data_dir / "aligned" / "mms_fa" / book
    verse_path, phones_path = save_forced_alignment(results, aligned_dir, book, chapter)

    # Display results table
    table = Table(title=f"MMS_FA Forced Alignment: {book} {chapter}")
    table.add_column("Verse", justify="left")
    table.add_column("Start (s)", justify="right")
    table.add_column("End (s)", justify="right")
    table.add_column("Words", justify="right")

    for r in results:
        word_count = len(r.get("words", []))
        table.add_row(
            r["verse_id"],
            f"{r['start_sec']:.2f}",
            f"{r['end_sec']:.2f}",
            str(word_count),
        )

    console.print(table)

    # Phone-level summary
    total_phones = sum(len(r.get("phones", [])) for r in results)
    console.print(f"[green]Phone-level tokens: {total_phones}[/green]")
    console.print(f"[green]Saved verse-level alignment to {verse_path}[/green]")
    console.print(f"[green]Saved phone-level alignment to {phones_path}[/green]")


@app.command("vibevoice")
def vibevoice_command(
    book: str = typer.Option(..., help="USX book code (e.g. GEN)"),
    chapter: int = typer.Option(..., help="Chapter number"),
    path: str = typer.Option(
        "both",
        help="Which path: 'asr' (ASR+RapidFuzz), 'direct', or 'both'",
    ),
) -> None:
    """Run VibeVoice alignment (ASR+RapidFuzz and/or direct)."""
    settings = get_settings()

    audio_path = settings.data_dir / "prepared" / "audio" / book / f"{chapter:03d}.wav"
    if not audio_path.exists():
        console.print(f"[red]Error: Audio file not found at {audio_path}[/red]")
        raise typer.Exit(1)

    # Load verses from MEK JSONL corpus
    mek_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not mek_path.exists():
        console.print(f"[red]Error: Text corpus not found at {mek_path}[/red]")
        raise typer.Exit(1)

    verses = []
    with open(mek_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            if verse.get("book") == book and verse.get("chapter") == chapter:
                verses.append(
                    {"verse_id": str(verse.get("verse")), "text": verse.get("text", "")}
                )

    if not verses:
        console.print(
            f"[red]Error: No verses found for {book} {chapter} in MEK corpus[/red]"
        )
        raise typer.Exit(1)

    # Save results to data/aligned/vibevoice/{book}/
    aligned_dir = settings.data_dir / "aligned" / "vibevoice" / book
    aligned_dir.mkdir(parents=True, exist_ok=True)

    if path in ("asr", "both"):
        console.print(
            f"[cyan]Running VibeVoice ASR+RapidFuzz for {book} {chapter}...[/cyan]"
        )
        try:
            asr_results = vibevoice_asr_match(audio_path, verses)
        except Exception as e:
            console.print(f"[red]VibeVoice ASR+RapidFuzz failed: {e}[/red]")
            raise typer.Exit(1)

        asr_path = aligned_dir / f"{chapter:03d}_asr.json"
        with open(asr_path, "w", encoding="utf-8") as f:
            json.dump(asr_results, f, ensure_ascii=False, indent=2)

        table = Table(title=f"VibeVoice ASR+RapidFuzz: {book} {chapter}")
        table.add_column("Verse", justify="left")
        table.add_column("Start (s)", justify="right")
        table.add_column("End (s)", justify="right")
        table.add_column("Confidence", justify="right")

        for r in asr_results:
            table.add_row(
                r["verse_id"],
                f"{r['start_sec']:.2f}",
                f"{r['end_sec']:.2f}",
                f"{r['confidence_score']:.1f}",
            )

        console.print(table)
        console.print(f"[green]Saved ASR+RapidFuzz results to {asr_path}[/green]")

    if path in ("direct", "both"):
        console.print(
            f"[cyan]Running VibeVoice direct alignment for {book} {chapter}...[/cyan]"
        )
        try:
            direct_results = vibevoice_direct(audio_path)
        except Exception as e:
            console.print(f"[red]VibeVoice direct alignment failed: {e}[/red]")
            raise typer.Exit(1)

        direct_path = aligned_dir / f"{chapter:03d}_direct.json"
        with open(direct_path, "w", encoding="utf-8") as f:
            json.dump(direct_results, f, ensure_ascii=False, indent=2)

        table = Table(title=f"VibeVoice Direct: {book} {chapter}")
        table.add_column("Text", justify="left")
        table.add_column("Start (s)", justify="right")
        table.add_column("End (s)", justify="right")
        table.add_column("Speaker", justify="left")

        for r in direct_results:
            # Truncate text for display
            display_text = r["text"][:60] + "..." if len(r["text"]) > 60 else r["text"]
            table.add_row(
                display_text,
                f"{r['start']:.2f}",
                f"{r['end']:.2f}",
                r.get("speaker", ""),
            )

        console.print(table)
        console.print(f"[green]Saved direct alignment results to {direct_path}[/green]")


@app.command("evaluate-gold")
def evaluate_gold_command(
    model: str = typer.Option(
        None, help="Specific model ID to run (defaults to all in gauntlet)"
    ),
) -> None:
    """Run transcription, alignment, and metrics calculation on 10 gold chapters."""
    settings = get_settings()

    # Define the 10 representative gold chapters
    GOLD_CHAPTERS = [
        ("TIT", 1),
        ("TIT", 2),
        ("TIT", 3),
        ("ZEP", 1),
        ("ZEP", 2),
        ("ZEP", 3),
        ("TOB", 1),
        ("TOB", 2),
        ("TOB", 3),
        ("TOB", 4),
    ]

    # Load canonical verses from MEK (primary source: all 73 books)
    text_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not text_path.exists():
        console.print(f"[red]Error: Text corpus not found at {text_path}[/red]")
        raise typer.Exit(1)

    all_verses = []
    with open(text_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            all_verses.append(
                {
                    "book": verse.get("book", ""),
                    "chapter": int(verse.get("chapter", 0)),
                    "verse_id": str(verse.get("verse", "")),
                    "text": verse.get("text", ""),
                }
            )

    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]
        if not models_to_run:
            console.print(
                f"[red]Error: Model {model} not found in gauntlet configuration[/red]"
            )
            raise typer.Exit(1)

    eval_dir = settings.data_dir / "processed" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {}

    for model_config in models_to_run:
        console.print(f"[cyan]Evaluating model: {model_config.id}[/cyan]")
        model_safe_name = model_config.id.replace("/", "_")

        table = Table(title=f"Gold Evaluation Metrics: {model_config.id}")
        table.add_column("Chapter", justify="left")
        table.add_column("Canonical Verses", justify="right")
        table.add_column("Aligned Verses", justify="right")
        table.add_column("Coverage (%)", justify="right")
        table.add_column("Avg Conf", justify="right")
        table.add_column("Median Conf", justify="right")
        table.add_column("Chrono Violations", justify="right")
        table.add_column("Time (s)", justify="right")

        model_results = []
        total_canonical = 0
        total_aligned = 0
        all_confidences = []
        total_violations = 0
        total_time = 0.0

        for book, chapter in GOLD_CHAPTERS:
            chapter_verses = [
                v for v in all_verses if v["book"] == book and v["chapter"] == chapter
            ]
            if not chapter_verses:
                console.print(
                    f"[yellow]Skipping {book} {chapter}: no canonical text verses[/yellow]"
                )
                continue

            audio_path = (
                settings.data_dir / "prepared" / "audio" / book / f"{chapter:03d}.wav"
            )
            if not audio_path.exists():
                console.print(
                    f"[yellow]Skipping {book} {chapter}: WAV audio file not found[/yellow]"
                )
                continue

            console.print(f"  Processing {book} Chapter {chapter}...")
            start_time = time.perf_counter()

            try:
                words = transcribe_audio(audio_path, model_config, settings.models_dir)
                matched = match_verses(chapter_verses, words)
            except Exception as e:
                console.print(f"[red]  Failed to process {book} {chapter}: {e}[/red]")
                continue

            elapsed = time.perf_counter() - start_time

            # Compute metrics
            num_canonical = len(chapter_verses)
            num_aligned = len(matched)
            coverage = (
                (num_aligned / num_canonical * 100.0) if num_canonical > 0 else 0.0
            )

            confidences = [
                m["confidence_score"] for m in matched if "confidence_score" in m
            ]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            med_conf = statistics.median(confidences) if confidences else 0.0

            violations = 0
            prev_start = None
            for m in matched:
                s_sec = m["start_sec"]
                if prev_start is not None and s_sec < prev_start:
                    violations += 1
                prev_start = s_sec

            # Save matched verses to filesystem
            out_path = eval_dir / f"{book}_{chapter:03d}_{model_safe_name}_matched.json"
            with open(out_path, "w", encoding="utf-8") as out_f:
                json.dump(matched, out_f, ensure_ascii=False, indent=2)

            table.add_row(
                f"{book} {chapter}",
                str(num_canonical),
                str(num_aligned),
                f"{coverage:.1f}%",
                f"{avg_conf:.1f}",
                f"{med_conf:.1f}",
                str(violations),
                f"{elapsed:.1f}",
            )

            # Update aggregates
            total_canonical += num_canonical
            total_aligned += num_aligned
            all_confidences.extend(confidences)
            total_violations += violations
            total_time += elapsed

            model_results.append(
                {
                    "book": book,
                    "chapter": chapter,
                    "canonical_verses": num_canonical,
                    "aligned_verses": num_aligned,
                    "coverage_pct": coverage,
                    "avg_confidence": avg_conf,
                    "median_confidence": med_conf,
                    "chronological_violations": violations,
                    "time_sec": elapsed,
                    "output_file": str(out_path),
                }
            )

        # Calculate final overall aggregates
        overall_coverage = (
            (total_aligned / total_canonical * 100.0) if total_canonical > 0 else 0.0
        )
        overall_avg_conf = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )
        overall_med_conf = (
            statistics.median(all_confidences) if all_confidences else 0.0
        )

        table.add_section()
        table.add_row(
            "Overall / Total",
            str(total_canonical),
            str(total_aligned),
            f"{overall_coverage:.1f}%",
            f"{overall_avg_conf:.1f}",
            f"{overall_med_conf:.1f}",
            str(total_violations),
            f"{total_time:.1f}",
            style="bold",
        )

        console.print(table)

        summary_data[model_config.id] = {
            "total_canonical": total_canonical,
            "total_aligned": total_aligned,
            "overall_coverage_pct": overall_coverage,
            "overall_avg_confidence": overall_avg_conf,
            "overall_median_confidence": overall_med_conf,
            "total_chronological_violations": total_violations,
            "total_time_sec": total_time,
            "chapters": model_results,
        }

    # Save summary report to JSON
    summary_path = eval_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump(summary_data, sf, ensure_ascii=False, indent=2)

    console.print(
        f"[green]Successfully saved master evaluation summary to {summary_path}[/green]"
    )


@app.command("setup")
def setup_command() -> None:
    """Pre-download model weights specified in the gauntlet configuration."""
    from huggingface_hub import snapshot_download  # type: ignore[import-untyped]

    settings = get_settings()
    models_dir = settings.models_dir

    for model in settings.gauntlet.models:
        console.print(f"[cyan]Downloading {model.id}...[/cyan]")
        local_dir = models_dir / model.id
        local_dir.mkdir(parents=True, exist_ok=True)
        try:
            snapshot_download(
                repo_id=model.id,
                local_dir=local_dir,
            )
            console.print(f"[green]Successfully downloaded {model.id}[/green]")
        except Exception as exc:
            console.print(f"[red]Failed to download {model.id}: {exc}[/red]")
            raise typer.Exit(1)


@app.command("evaluate")
def evaluate_command(
    book: str = typer.Option(None, help="USX book code (evaluate single book)"),
    chapter: int = typer.Option(None, help="Chapter number (evaluate single chapter)"),
    gold: bool = typer.Option(False, help="Use gold chapters for evaluation"),
    model: str = typer.Option(None, help="Specific model ID to evaluate"),
) -> None:
    """Evaluate and compare alignment approaches with WER, timestamp accuracy, and cost metrics."""
    settings = get_settings()

    # Gold chapters (same as evaluate-gold)
    GOLD_CHAPTERS = [
        ("TIT", 1),
        ("TIT", 2),
        ("TIT", 3),
        ("ZEP", 1),
        ("ZEP", 2),
        ("ZEP", 3),
        ("TOB", 1),
        ("TOB", 2),
        ("TOB", 3),
        ("TOB", 4),
    ]

    # Determine chapters to evaluate
    if gold:
        chapters = GOLD_CHAPTERS
    elif book and chapter:
        chapters = [(book, chapter)]
    else:
        console.print("[red]Error: Specify --gold or both --book and --chapter[/red]")
        raise typer.Exit(1)

    # Load canonical verses from MEK JSONL
    text_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not text_path.exists():
        console.print(f"[red]Error: Text corpus not found at {text_path}[/red]")
        raise typer.Exit(1)

    all_verses: list[dict[str, Any]] = []
    with open(text_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            all_verses.append(
                {
                    "book": verse.get("book", ""),
                    "chapter": int(verse.get("chapter", 0)),
                    "verse_id": str(verse.get("verse", "")),
                    "text": verse.get("text", ""),
                }
            )

    # Select models
    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]
        if not models_to_run:
            console.print(
                f"[red]Error: Model {model} not found in gauntlet configuration[/red]"
            )
            raise typer.Exit(1)

    eval_dir = settings.data_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[dict[str, Any]] = []

    for model_config in models_to_run:
        console.print(f"[cyan]Evaluating model: {model_config.id}[/cyan]")
        model_safe_name = model_config.id.replace("/", "_")

        model_wers: list[float] = []
        model_start_devs: list[float] = []
        model_end_devs: list[float] = []
        model_confidences: list[float] = []
        model_cost = 0.0
        model_time = 0.0
        model_aligned = 0
        model_total = 0
        model_error: str | None = None

        for bk, ch in chapters:
            chapter_verses = [
                v for v in all_verses if v["book"] == bk and v["chapter"] == ch
            ]
            if not chapter_verses:
                console.print(f"[yellow]Skipping {bk} {ch}: no canonical text[/yellow]")
                continue

            audio_path = settings.data_dir / "prepared" / "audio" / bk / f"{ch:03d}.wav"
            if not audio_path.exists():
                console.print(f"[yellow]Skipping {bk} {ch}: WAV not found[/yellow]")
                continue

            # Check cache first (D-35)
            cached = load_cached_result(model_safe_name, bk, ch, settings.data_dir)
            if cached is not None:
                console.print(f"  [dim]Using cached result for {bk} {ch}[/dim]")
                matched = cached
            else:
                console.print(f"  Processing {bk} Chapter {ch}...")
                start_time = time.perf_counter()
                try:
                    words = transcribe_audio(
                        audio_path, model_config, settings.models_dir
                    )
                    matched = match_verses(chapter_verses, words)
                except Exception as e:
                    console.print(f"[red]  Failed: {e}[/red]")
                    model_error = str(e)
                    break  # D-38: fail-fast

                elapsed = time.perf_counter() - start_time
                model_time += elapsed

                # Save to cache (D-36)
                save_cached_result(matched, model_safe_name, bk, ch, settings.data_dir)

            # Compute metrics
            num_canonical = len(chapter_verses)
            num_aligned = len(matched)
            model_aligned += num_aligned
            model_total += num_canonical

            # WER: compare transcribed text to canonical text
            transcribed_text = " ".join(m.get("verse_id", "") for m in matched)
            canonical_text = " ".join(v["verse_id"] for v in chapter_verses)
            # Use actual verse text for WER if available
            if matched and "text" in matched[0]:
                transcribed_text = " ".join(m.get("text", "") for m in matched)
                canonical_text = " ".join(v["text"] for v in chapter_verses)

            wer = compute_wer(canonical_text, transcribed_text)
            model_wers.append(wer)

            # Timestamp accuracy (against self for now — gold standard needed)
            if len(matched) >= 2:
                # Use consecutive verse pairs as proxy for deviation
                for i in range(1, len(matched)):
                    pred = [
                        {
                            "start": matched[i - 1]["start_sec"],
                            "end": matched[i - 1]["end_sec"],
                        }
                    ]
                    gold_ts = [
                        {"start": matched[i]["start_sec"], "end": matched[i]["end_sec"]}
                    ]
                    acc = compute_timestamp_accuracy(pred, gold_ts)
                    model_start_devs.append(acc["mean_start_deviation"])
                    model_end_devs.append(acc["mean_end_deviation"])

            # Confidence
            confidences = [
                m["confidence_score"] for m in matched if "confidence_score" in m
            ]
            model_confidences.extend(confidences)

        if model_error:
            # D-39: include failed models in report with error message
            all_results.append(
                {
                    "model": model_config.id,
                    "book": book or "gold",
                    "chapter": chapter or 0,
                    "wer": 1.0,
                    "mean_start_deviation": 0.0,
                    "mean_end_deviation": 0.0,
                    "avg_confidence": 0.0,
                    "cost_usd": 0.0,
                    "time_sec": 0.0,
                    "aligned_verses": 0,
                    "total_verses": 0,
                    "error": model_error,
                }
            )
            console.print(f"[red]Model {model_config.id} failed: {model_error}[/red]")
            continue

        avg_wer = sum(model_wers) / len(model_wers) if model_wers else 0.0
        avg_start_dev = (
            sum(model_start_devs) / len(model_start_devs) if model_start_devs else 0.0
        )
        avg_end_dev = (
            sum(model_end_devs) / len(model_end_devs) if model_end_devs else 0.0
        )
        avg_conf = (
            sum(model_confidences) / len(model_confidences)
            if model_confidences
            else 0.0
        )

        result = {
            "model": model_config.id,
            "book": book or "gold",
            "chapter": chapter or 0,
            "wer": avg_wer,
            "mean_start_deviation": avg_start_dev,
            "mean_end_deviation": avg_end_dev,
            "avg_confidence": avg_conf,
            "cost_usd": model_cost,
            "time_sec": model_time,
            "aligned_verses": model_aligned,
            "total_verses": model_total,
        }
        all_results.append(result)

    if not all_results:
        console.print("[red]No models produced results[/red]")
        raise typer.Exit(1)

    # Build and display comparison table (D-34)
    table = build_comparison_table(all_results)
    console.print(table)

    # Save report to data/evaluation/ (D-31)
    jsonl_path, summary_path = save_evaluation_report(all_results, eval_dir)
    console.print(f"[green]Saved JSONL report to {jsonl_path}[/green]")
    console.print(f"[green]Saved summary to {summary_path}[/green]")
