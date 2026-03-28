const STATUS_META = {
  pending: {
    label: 'Pending Review',
    tone: 'bg-amber-50 text-amber-800 ring-amber-200',
    dot: 'bg-amber-500'
  },
  not_started: {
    label: 'Queued',
    tone: 'bg-slate-100 text-slate-700 ring-slate-200',
    dot: 'bg-slate-400'
  },
  assigned: {
    label: 'Dispatched',
    tone: 'bg-sky-50 text-sky-800 ring-sky-200',
    dot: 'bg-sky-500'
  },
  in_progress: {
    label: 'In Service',
    tone: 'bg-blue-50 text-blue-800 ring-blue-200',
    dot: 'bg-blue-500'
  },
  completed: {
    label: 'Completed',
    tone: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    dot: 'bg-emerald-500'
  },
  on_hold: {
    label: 'Needs Attention',
    tone: 'bg-rose-50 text-rose-800 ring-rose-200',
    dot: 'bg-rose-500'
  },
  cancelled: {
    label: 'Cancelled',
    tone: 'bg-zinc-100 text-zinc-700 ring-zinc-200',
    dot: 'bg-zinc-400'
  },
  unknown: {
    label: 'Unknown',
    tone: 'bg-slate-100 text-slate-700 ring-slate-200',
    dot: 'bg-slate-400'
  }
};

const SIZE_MAP = {
  sm: 'px-2.5 py-1 text-[11px]',
  md: 'px-3 py-1.5 text-xs'
};

const normalizeStatus = (status) => String(status || '').toLowerCase().replace(/\s+/g, '_');

export const formatStatusLabel = (status) => {
  const normalizedStatus = normalizeStatus(status);
  if (STATUS_META[normalizedStatus]) {
    return STATUS_META[normalizedStatus].label;
  }
  return normalizedStatus
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || STATUS_META.unknown.label;
};

export default function StatusBadge({ status, size = 'md', className = '' }) {
  const normalizedStatus = normalizeStatus(status);
  const meta = STATUS_META[normalizedStatus] || STATUS_META.unknown;

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full ring-1 ring-inset ${meta.tone} ${
        SIZE_MAP[size] || SIZE_MAP.md
      } ${className}`.trim()}
    >
      <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
      <span className="whitespace-nowrap font-semibold tracking-[0.02em]">{meta.label}</span>
    </span>
  );
}
