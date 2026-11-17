import Link from "next/link";
import { ArrowLeft, CheckCircle, AlertTriangle, Lightbulb, Terminal, ChevronRight } from "lucide-react";
import { ReactNode } from "react";

export function WikiLayout({
  title,
  subtitle,
  description,
  color,
  children,
}: {
  title: string;
  subtitle: string;
  description: string;
  color: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link
            href="/wiki"
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Wiki
          </Link>
          <ChevronRight className="w-3 h-3 text-gray-300" />
          <span className="text-sm font-medium text-gray-900">{title}</span>
        </div>
      </div>

      {/* Hero */}
      <div className={`bg-gradient-to-r ${color} text-white`}>
        <div className="max-w-4xl mx-auto px-6 py-10">
          <div className="text-white/70 text-xs font-semibold uppercase tracking-widest mb-2">
            {subtitle}
          </div>
          <h1 className="text-3xl font-bold mb-3">{title}</h1>
          <p className="text-white/80 text-sm max-w-2xl leading-relaxed">{description}</p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-10 space-y-10">{children}</div>

      <footer className="max-w-4xl mx-auto px-6 pb-10 text-center text-xs text-gray-400">
        Usage interne — <Link href="/wiki" className="hover:underline">radarapp.fr/wiki</Link>
      </footer>
    </div>
  );
}

export function TpSection({
  number,
  title,
  duration,
  children,
}: {
  number: string;
  title: string;
  duration?: string;
  children: ReactNode;
}) {
  return (
    <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="bg-indigo-600 text-white text-xs font-bold px-2.5 py-1 rounded-lg">
            {number}
          </span>
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        </div>
        {duration && (
          <span className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
            ⏱ {duration}
          </span>
        )}
      </div>
      <div className="px-6 py-5 space-y-5">{children}</div>
    </section>
  );
}

export function Phase({
  number,
  title,
  children,
}: {
  number: number | string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="border-l-2 border-indigo-200 pl-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="bg-indigo-50 text-indigo-700 text-xs font-semibold px-2 py-0.5 rounded">
          Phase {number}
        </span>
        <h3 className="font-semibold text-gray-800">{title}</h3>
      </div>
      <div className="space-y-2 text-sm text-gray-700 leading-relaxed">{children}</div>
    </div>
  );
}

export function Steps({ items }: { items: string[] }) {
  return (
    <ol className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 text-sm text-gray-700">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center mt-0.5">
            {i + 1}
          </span>
          <span dangerouslySetInnerHTML={{ __html: item }} />
        </li>
      ))}
    </ol>
  );
}

export function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  return (
    <div className="rounded-xl overflow-hidden border border-gray-200">
      <div className="bg-gray-800 flex items-center gap-2 px-4 py-2">
        <Terminal className="w-3.5 h-3.5 text-gray-400" />
        <span className="text-xs text-gray-400 font-mono">{language}</span>
      </div>
      <pre className="bg-gray-900 text-gray-100 p-4 text-xs overflow-x-auto leading-relaxed font-mono whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  );
}

export function Tip({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4">
      <Lightbulb className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
      <div className="text-sm text-amber-800 leading-relaxed">{children}</div>
    </div>
  );
}

export function Warning({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
      <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
      <div className="text-sm text-red-800 leading-relaxed">{children}</div>
    </div>
  );
}

export function Checklist({ items }: { items: string[] }) {
  return (
    <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle className="w-4 h-4 text-green-600" />
        <span className="text-sm font-semibold text-green-800">Critères de réussite</span>
      </div>
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2 text-sm text-green-700">
          <span className="text-green-400 flex-shrink-0 mt-0.5">✓</span>
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}

export function InfoTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: string[][];
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="text-left px-4 py-3 font-semibold text-gray-700 text-xs uppercase tracking-wide">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 text-gray-700 font-mono text-xs">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
