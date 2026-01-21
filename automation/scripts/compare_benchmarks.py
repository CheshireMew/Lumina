"""
Compare benchmark results between baseline and current runs

Usage:
    python compare_benchmarks.py --baseline baseline.json --current current.json --threshold 1.2
"""
import sys
import json
import argparse
from pathlib import Path


def load_results(filepath):
    """Load benchmark JSON results"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get('benchmarks', [])


def compare_benchmarks(baseline, current, threshold=1.2):
    """Compare two benchmark runs"""
    baseline_dict = {b['name']: b for b in baseline}
    current_dict = {b['name']: b for b in current}

    results = []
    for name in baseline_dict:
        if name not in current_dict:
            continue

        base_mean = baseline_dict[name]['stats']['mean']
        curr_mean = current_dict[name]['stats']['mean']

        ratio = curr_mean / base_mean if base_mean > 0 else 1.0
        is_regress = ratio > threshold
        is_improve = ratio < (1 / threshold)

        results.append({
            'name': name,
            'baseline_mean': base_mean,
            'current_mean': curr_mean,
            'ratio': ratio,
            'regression': is_regress,
            'improvement': is_improve
        })

    return results


def format_report(results, threshold):
    """Format comparison as Markdown"""
    lines = [
        "# Performance Comparison Report",
        f"Threshold: {threshold:.1f}x (warning above this ratio)",
        "",
        "## Results",
        "",
        "| Benchmark | Baseline | Current | Ratio | Status |",
        "|-----------|----------|---------|-------|--------|"
    ]

    regressions = 0
    improvements = 0

    for r in results:
        name = r['name'].split('[')[0].strip()
        baseline = f"{r['baseline_mean']:.6f}"
        current = f"{r['current_mean']:.6f}"
        ratio = f"{r['ratio']:.2f}x"

        if r['regression']:
            status = f":rotating_light: +{((r['ratio']-1)*100):.1f}%"
            regressions += 1
        elif r['improvement']:
            status = f":zap: {((r['ratio']-1)*100):.1f}%"
            improvements += 1
        else:
            status = ":white_check_mark: Stable"

        lines.append(f"| {name} | {baseline} | {current} | {ratio} | {status} |")

    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total benchmarks: {len(results)}",
        f"- Regressions: {regressions}",
        f"- Improvements: {improvements}",
        f"- Stable: {len(results) - regressions - improvements}"
    ])

    if regressions > 0:
        lines.extend([
            "",
            ":warning: Performance regressions detected!"
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Compare pytest benchmark results')
    parser.add_argument('--baseline', required=True, help='Baseline results JSON')
    parser.add_argument('--current', required=True, help='Current results JSON')
    parser.add_argument('--threshold', type=float, default=1.2, help='Regression threshold')
    parser.add_argument('--output', help='Output report file')
    args = parser.parse_args()

    # Load results
    baseline = load_results(args.baseline)
    current = load_results(args.current)

    # Compare
    results = compare_benchmarks(baseline, current, args.threshold)

    # Generate report
    report = format_report(results, args.threshold)

    # Output
    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)

    # Exit code based on regressions
    if any(r['regression'] for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
