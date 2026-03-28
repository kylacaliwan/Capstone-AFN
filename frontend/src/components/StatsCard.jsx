export default function StatsCard({ title, value, color }) {
  return (
    <div className="card p-4 sm:p-5">
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-bold sm:text-3xl ${color || 'text-slate-800'}`}>{value}</p>
      <div className="mt-1 h-1 w-16 rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-sky-500"></div>
    </div>
  );
}
