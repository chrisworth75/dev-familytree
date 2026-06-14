import { TIER } from '../config'

// Anti-confusion aid: when running multiple deploy tiers side by side, the app
// announces which one you're looking at. Driven by window.__ENV__.TIER, so the
// same image shows a different badge per environment. Hidden when TIER is unset.
const COLORS = { '1': '#1a7f37', '2': '#bf8700', '3': '#0969da' } // green / amber / blue

export default function TierBanner() {
  if (!TIER) return null
  const bg = COLORS[String(TIER).trim()[0]] || '#57606a'
  return (
    <div
      style={{
        position: 'fixed', bottom: 8, right: 8, zIndex: 9999,
        background: bg, color: 'white', padding: '6px 10px', borderRadius: 6,
        font: '600 12px/1 system-ui, sans-serif', letterSpacing: '0.04em',
        textTransform: 'uppercase', boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
        pointerEvents: 'none',
      }}
    >
      Tier {TIER}
    </div>
  )
}
