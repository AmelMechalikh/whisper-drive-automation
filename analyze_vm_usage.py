#!/usr/bin/env python3
"""Analyze VM usage from GCP logs to estimate costs"""

import subprocess
import json
from datetime import datetime, timedelta
from collections import defaultdict

def get_vm_events(days=30):
    """Get VM start/stop events from logs"""
    cmd = [
        'gcloud', 'logging', 'read',
        'resource.type="gce_instance" AND '
        '(protoPayload.methodName="v1.compute.instances.start" OR '
        'protoPayload.methodName="v1.compute.instances.stop")',
        f'--limit=500',
        '--format=json',
        f'--freshness={days}d'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        return []
    except Exception as e:
        print(f"Error getting logs: {e}")
        return []

def analyze_usage(events):
    """Analyze VM usage patterns"""
    vm_stats = defaultdict(lambda: {
        'starts': 0,
        'stops': 0,
        'dates': set(),
        'events': []
    })

    for event in events:
        try:
            timestamp = event.get('timestamp', '')
            method = event.get('protoPayload', {}).get('methodName', '')
            resource = event.get('protoPayload', {}).get('resourceName', '')

            # Extract VM name
            if 'whisper-cpu-worker' in resource:
                vm_name = 'whisper-cpu-worker'
            elif 'highlights-worker-vm' in resource:
                vm_name = 'highlights-worker-vm'
            else:
                continue

            # Parse timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            date = dt.date()

            vm_stats[vm_name]['events'].append({
                'time': dt,
                'method': method,
                'date': date
            })
            vm_stats[vm_name]['dates'].add(date)

            if 'start' in method:
                vm_stats[vm_name]['starts'] += 1
            elif 'stop' in method:
                vm_stats[vm_name]['stops'] += 1

        except Exception as e:
            continue

    return vm_stats

def estimate_monthly_cost(vm_stats):
    """Estimate monthly costs based on usage patterns"""

    # Pricing (europe-west1)
    prices = {
        'whisper-cpu-worker': 0.39,  # n2-standard-8
        'highlights-worker-vm': 0.19  # n2-standard-4
    }

    print("\n" + "="*70)
    print("📊 ANALYSE D'UTILISATION DES VMs (30 derniers jours)")
    print("="*70 + "\n")

    total_estimated = 0

    for vm_name, stats in sorted(vm_stats.items()):
        print(f"🖥️  {vm_name}")
        print("-" * 70)
        print(f"   Nombre de démarrages: {stats['starts']}")
        print(f"   Nombre d'arrêts: {stats['stops']}")
        print(f"   Jours d'activité: {len(stats['dates'])} jours")

        # Estimate hours based on start events
        # Assume average session is 10-15 minutes if auto-shutdown works
        avg_session_hours = 0.17  # ~10 min per session
        estimated_hours_month = stats['starts'] * avg_session_hours

        # If more starts than stops, VM might be running continuously
        if stats['starts'] > stats['stops'] + 5:
            print(f"   ⚠️  Plus de starts que de stops - VM peut rester allumée")
            # Estimate based on days active
            estimated_hours_month = len(stats['dates']) * 2  # 2h per active day

        hourly_rate = prices.get(vm_name, 0.2)
        monthly_cost = estimated_hours_month * hourly_rate

        print(f"   Heures estimées/mois: ~{estimated_hours_month:.1f}h")
        print(f"   Tarif horaire: ${hourly_rate}/h")
        print(f"   💰 Coût estimé: ${monthly_cost:.2f}/mois")
        print()

        total_estimated += monthly_cost

    print("="*70)
    print(f"💵 TOTAL ESTIMÉ VMs: ${total_estimated:.2f}/mois")
    print("="*70)
    print("\n📋 DÉTAIL COMPLET:")
    print(f"   - Cloud Run (2 services): ~$1-2/mois")
    print(f"   - Cloud Scheduler: $0/mois (gratuit)")
    print(f"   - Container Registry: ~$0.10/mois")
    print(f"   - VMs (calculé ci-dessus): ${total_estimated:.2f}/mois")
    print("-" * 70)
    print(f"   🎯 TOTAL INFRASTRUCTURE: ${total_estimated + 2:.2f}/mois")
    print("="*70 + "\n")

if __name__ == '__main__':
    print("⏳ Récupération des logs GCP (30 derniers jours)...")
    events = get_vm_events(30)

    if not events:
        print("❌ Aucun événement trouvé dans les logs")
    else:
        print(f"✅ {len(events)} événements trouvés\n")
        vm_stats = analyze_usage(events)
        estimate_monthly_cost(vm_stats)
