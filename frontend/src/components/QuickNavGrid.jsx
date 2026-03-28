import { Link } from 'react-router-dom';

export default function QuickNavGrid({ items }) {
  return (
    <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Link
          key={item.label}
          to={item.path}
          className="card p-4 transition hover:-translate-y-1 hover:shadow-xl sm:p-5"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold text-slate-800 sm:text-lg">{item.label}</h3>
                {item.badge !== undefined && item.badge !== null && (
                  <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${item.badgeTone || 'bg-slate-100 text-slate-700'}`}>
                    {item.badge}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-slate-500">{item.description}</p>
            </div>
            <div className="shrink-0 text-xl text-primary sm:text-2xl">{item.icon}</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
