// Small dependency-free SVG chart primitives used across the dashboard.
// Hand-rolled rather than pulling in a charting library — the shapes needed
// here (a donut, a sparkline, a bar list) are simple enough that a library
// would add more weight than value.

export function Donut({
  value, size = 96, stroke = 10, color = "var(--accent)", track = "var(--panel-3)", label, sub,
}: {
  value: number; size?: number; stroke?: number; color?: string; track?: string; label?: string; sub?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value));
  const dash = c * pct;
  return (
    <div className="donut-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dash} ${c - dash}`} strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="donut-center">
        <div className="donut-value">{label ?? `${Math.round(pct * 100)}%`}</div>
        {sub && <div className="donut-sub">{sub}</div>}
      </div>
    </div>
  );
}

export function Sparkline({
  points, width = 280, height = 64, color = "var(--accent)", fill = true,
}: {
  points: number[]; width?: number; height?: number; color?: string; fill?: boolean;
}) {
  if (points.length < 2) return <svg width={width} height={height} />;
  const max = Math.max(...points, 1e-9);
  const min = Math.min(...points, 0);
  const range = max - min || 1;
  const step = width / (points.length - 1);
  const coords = points.map((p, i) => [i * step, height - ((p - min) / range) * (height - 6) - 3]);
  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${path} L${width},${height} L0,${height} Z`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="sparkline">
      {fill && <path d={area} fill={color} opacity={0.12} />}
      <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function BarMini({
  items, formatValue,
}: {
  items: { label: string; value: number; color?: string }[];
  formatValue?: (v: number) => string;
}) {
  const max = Math.max(...items.map((i) => i.value), 1e-9);
  return (
    <div className="barmini">
      {items.map((it) => (
        <div className="barmini-row" key={it.label}>
          <span className="barmini-label">{it.label}</span>
          <div className="barmini-track">
            <div
              className="barmini-fill"
              style={{ width: `${(it.value / max) * 100}%`, background: it.color ?? "var(--accent)" }}
            />
          </div>
          <span className="barmini-value">{formatValue ? formatValue(it.value) : it.value}</span>
        </div>
      ))}
    </div>
  );
}

export function PieMini({
  items, size = 120, stroke = 22,
}: {
  items: { label: string; value: number; color: string }[]; size?: number; stroke?: number;
}) {
  const total = items.reduce((s, i) => s + i.value, 0) || 1;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="pie-mini">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--panel-3)" strokeWidth={stroke} />
        {items.filter((it) => it.value > 0).map((it) => {
          const pct = it.value / total;
          const dash = c * pct;
          const el = (
            <circle
              key={it.label} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={it.color} strokeWidth={stroke}
              strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={-offset}
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          );
          offset += dash;
          return el;
        })}
      </svg>
      <div className="pie-mini-legend">
        {items.map((it) => (
          <div className="pie-mini-legend-row" key={it.label}>
            <span className="pie-mini-dot" style={{ background: it.color }} />
            <span className="pie-mini-label">{it.label}</span>
            <span className="pie-mini-value">{Math.round((it.value / total) * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function VerticalBars({
  items, height = 140,
}: {
  items: { label: string; value: number; color?: string }[]; height?: number;
}) {
  const max = Math.max(...items.map((i) => i.value), 1e-9);
  return (
    <div className="vbars" style={{ height }}>
      {items.map((it) => (
        <div className="vbar-col" key={it.label}>
          <div className="vbar-track" style={{ height: height - 24 }}>
            <div
              className="vbar-fill"
              style={{ height: `${(it.value / max) * 100}%`, background: it.color ?? "var(--accent)" }}
            />
          </div>
          <div className="vbar-label">{it.label}</div>
        </div>
      ))}
    </div>
  );
}
