// A small, consistent icon set. Emoji render differently (and often poorly)
// across OS/browser combinations, which is a big part of why an ad-hoc mix of
// them reads as unpolished. These are plain stroked SVGs at a fixed weight.
type Props = { size?: number; className?: string };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function PlayIcon({ size = 14, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <polygon points="6 3 20 12 6 21 6 3" />
    </svg>
  );
}

export function CheckCircle({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

export function AlertTriangle({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

export function XCircle({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

export function ShieldIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
    </svg>
  );
}

export function ZapIcon({ size = 14, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

export function RefreshIcon({ size = 14, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

export function InfoIcon({ size = 14, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

export function TruckIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <rect x="1" y="3" width="15" height="13" />
      <path d="M16 8h4l3 3v5h-7V8Z" />
      <circle cx="5.5" cy="18.5" r="2.5" />
      <circle cx="18.5" cy="18.5" r="2.5" />
    </svg>
  );
}

export function CloudIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M17.5 19a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.6 1.7A4 4 0 0 0 6.5 19h11Z" />
    </svg>
  );
}

export function GridIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function SearchCarIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M3 12l1.6-4.8A2 2 0 0 1 6.5 6h11a2 2 0 0 1 1.9 1.2L21 12" />
      <path d="M3 12h18v4a1 1 0 0 1-1 1h-1.5a1 1 0 0 1-1-1v-1H6.5v1a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4Z" />
      <circle cx="7.5" cy="16.5" r="1.2" />
      <circle cx="16.5" cy="16.5" r="1.2" />
    </svg>
  );
}

export function ActivityIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

export function FlaskIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M9 2h6" />
      <path d="M10 2v6.2L4.5 18a2 2 0 0 0 1.8 3h11.4a2 2 0 0 0 1.8-3L14 8.2V2" />
      <path d="M7 15h10" />
    </svg>
  );
}

export function ClipboardIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
      <line x1="8" y1="11" x2="16" y2="11" />
      <line x1="8" y1="15" x2="16" y2="15" />
    </svg>
  );
}

export function BarChartIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <line x1="4" y1="20" x2="4" y2="12" />
      <line x1="10" y1="20" x2="10" y2="6" />
      <line x1="16" y1="20" x2="16" y2="14" />
      <line x1="21" y1="20" x2="21" y2="9" />
    </svg>
  );
}

export function SettingsIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  );
}

export function SearchIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export function BellIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

export function ChevronDownIcon({ size = 16, className }: Props) {
  return (
    <svg {...base(size)} className={className}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
