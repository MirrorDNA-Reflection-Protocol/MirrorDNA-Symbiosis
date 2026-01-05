#!/usr/bin/env python3
"""
SUPERAGENT — Version Scanner
Scans repos for version drift between specs and implementations.

Usage:
    python version_scanner.py                    # Scan all known projects
    python version_scanner.py --project mirrorgate  # Scan specific project
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Project definitions
PROJECTS = {
    "mirrorgate": {
        "impl_paths": [
            Path.home() / "Documents/GitHub/activemirror-site/src/utils/mirrorGate.js",
            Path.home() / "Documents/GitHub/activemirror-site/src/pages/Demo.jsx",
        ],
        "spec_paths": [
            Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault",
        ],
        "spec_pattern": "*MirrorGate*.md",
        "version_regex": r'MirrorGate v(\d+\.?\d*)',
    },
    "mirrorbrain": {
        "impl_paths": [
            Path.home() / "Documents/MirrorBrain-Setup",
        ],
        "spec_paths": [
            Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault",
        ],
        "spec_pattern": "*MirrorBrain*.md",
        "version_regex": r'MirrorBrain v(\d+\.?\d*)',
    },
    "spine": {
        "impl_paths": [
            Path.home() / "Documents/MirrorDNA-Symbiosis/spine",
        ],
        "spec_paths": [
            Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault",
        ],
        "spec_pattern": "*spine*.md",
        "version_regex": r'Spine v(\d+\.?\d*)',
    }
}

VAULT_PATH = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
REPORT_PATH = VAULT_PATH / "Superagent/version_drift_report.md"


def extract_versions(path: Path, regex: str) -> List[Tuple[str, str]]:
    """Extract version strings from a file."""
    versions = []
    if not path.exists():
        return versions
    
    if path.is_file():
        try:
            content = path.read_text(errors='ignore')
            matches = re.findall(regex, content, re.IGNORECASE)
            for m in matches:
                versions.append((str(path), m))
        except:
            pass
    return versions


def scan_directory(directory: Path, pattern: str, regex: str) -> List[Tuple[str, str]]:
    """Scan directory for files matching pattern and extract versions."""
    versions = []
    if not directory.exists():
        return versions
    
    for file in directory.rglob(pattern):
        # Skip archive/backup directories
        if '_Archive' in str(file) or 'backup' in str(file).lower():
            continue
        versions.extend(extract_versions(file, regex))
    
    return versions


def scan_project(project_name: str, config: Dict) -> Dict:
    """Scan a single project for version drift."""
    result = {
        "project": project_name,
        "impl_versions": [],
        "spec_versions": [],
        "drift_detected": False,
        "issues": []
    }
    
    regex = config.get('version_regex', r'v(\d+\.?\d*)')
    
    # Scan implementations
    for impl_path in config.get('impl_paths', []):
        if impl_path.is_file():
            result['impl_versions'].extend(extract_versions(impl_path, regex))
        elif impl_path.is_dir():
            for ext in ['*.js', '*.jsx', '*.py', '*.ts']:
                for file in impl_path.rglob(ext):
                    if '_Archive' not in str(file):
                        result['impl_versions'].extend(extract_versions(file, regex))
    
    # Scan specs
    for spec_path in config.get('spec_paths', []):
        if spec_path.is_dir():
            pattern = config.get('spec_pattern', '*.md')
            result['spec_versions'].extend(scan_directory(spec_path, pattern, regex))
    
    # Analyze drift
    impl_nums = set(v[1] for v in result['impl_versions'])
    spec_nums = set(v[1] for v in result['spec_versions'])
    
    if impl_nums and spec_nums:
        max_impl = max(float(v) for v in impl_nums)
        max_spec = max(float(v) for v in spec_nums)
        
        if max_spec > max_impl:
            result['drift_detected'] = True
            result['issues'].append(f"Spec v{max_spec} exists but implementation is at v{max_impl}")
        elif max_impl > max_spec:
            result['issues'].append(f"Implementation v{max_impl} may not have a corresponding spec")
    
    return result


def generate_report(results: List[Dict]) -> str:
    """Generate markdown report."""
    lines = [
        "# ⟡ Version Drift Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Scanner:** Superagent v1.0",
        "",
        "---",
        ""
    ]
    
    drift_count = sum(1 for r in results if r['drift_detected'])
    
    lines.append(f"## Summary: {drift_count}/{len(results)} projects with drift detected")
    lines.append("")
    
    for result in results:
        status = "🔴 DRIFT" if result['drift_detected'] else "🟢 OK"
        lines.append(f"### {result['project']} — {status}")
        lines.append("")
        
        if result['impl_versions']:
            impl_vers = sorted(set(v[1] for v in result['impl_versions']), key=float, reverse=True)
            lines.append(f"**Implementation versions:** {', '.join(f'v{v}' for v in impl_vers[:3])}")
        else:
            lines.append("**Implementation versions:** None found")
        
        if result['spec_versions']:
            spec_vers = sorted(set(v[1] for v in result['spec_versions']), key=float, reverse=True)
            lines.append(f"**Spec versions:** {', '.join(f'v{v}' for v in spec_vers[:5])}")
        else:
            lines.append("**Spec versions:** None found")
        
        if result['issues']:
            lines.append("")
            lines.append("**Issues:**")
            for issue in result['issues']:
                lines.append(f"- ⚠️ {issue}")
        
        lines.append("")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan for version drift")
    parser.add_argument("--project", "-p", help="Specific project to scan")
    parser.add_argument("--output", "-o", help="Output report path")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    # Determine which projects to scan
    if args.project:
        if args.project not in PROJECTS:
            print(f"❌ Unknown project: {args.project}")
            print(f"   Available: {', '.join(PROJECTS.keys())}")
            return
        projects = {args.project: PROJECTS[args.project]}
    else:
        projects = PROJECTS
    
    # Scan
    print("⟡ Scanning for version drift...\n")
    results = []
    for name, config in projects.items():
        print(f"  Scanning {name}...")
        result = scan_project(name, config)
        results.append(result)
        status = "⚠️ DRIFT" if result['drift_detected'] else "✅"
        print(f"    {status}")
    
    # Output
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        report = generate_report(results)
        print("\n" + report)
        
        # Save report
        output_path = Path(args.output) if args.output else REPORT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"\n📄 Report saved to: {output_path}")


if __name__ == "__main__":
    main()
