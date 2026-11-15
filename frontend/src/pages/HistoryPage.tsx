import React, { useState, useEffect } from 'react';
import { History, Search, Download, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../services/api';
import { DetectionItem } from '../types';

export const HistoryPage: React.FC = () => {
  const [detections, setDetections] = useState<DetectionItem[]>([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [minConf, setMinConf] = useState<number>(0.0);

  const fetchHistory = async () => {
    try {
      const res = await api.getDetections({
        category: category || undefined,
        class_name: searchTerm || undefined,
        min_confidence: minConf,
        page,
        page_size: 15
      });
      setDetections(res.detections || []);
      setTotalRecords(res.total_records || 0);
    } catch (e) {
      console.error('Failed to load history:', e);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, category, minConf]);

  const handleExportCSV = () => {
    if (!detections.length) return;
    const headers = ['ID', 'Category', 'Class', 'Confidence', 'Timestamp', 'BBox'];
    const rows = detections.map(d => [
      d.id,
      d.category,
      d.class_name,
      d.confidence,
      new Date(d.timestamp * 1000).toISOString(),
      `"${d.bbox.join(',')}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `road_ai_detections_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold font-mono text-white flex items-center space-x-2">
            <History className="w-5 h-5 text-cyan-400" />
            <span>SEARCHABLE DETECTION INCIDENT LOGS</span>
          </h2>
          <p className="text-xs text-gray-400">Audit trail of all road damage events and traffic entities detected</p>
        </div>

        <button
          onClick={handleExportCSV}
          className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-800 text-cyan-400 border border-gray-700 hover:bg-gray-750 text-xs font-mono font-semibold"
        >
          <Download className="w-4 h-4" />
          <span>EXPORT CSV</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 flex flex-wrap gap-4 items-center">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search class (e.g. pothole, car)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchHistory()}
            className="w-full bg-gray-950 border border-gray-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-gray-500 font-mono focus:border-cyan-500 focus:outline-none"
          />
        </div>

        {/* Category Dropdown */}
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-1.5 text-xs font-mono text-gray-300 focus:border-cyan-500 focus:outline-none"
        >
          <option value="">All Categories</option>
          <option value="road_damage">Road Damage Only</option>
          <option value="general_object">Traffic Objects Only</option>
        </select>

        {/* Confidence Filter */}
        <div className="flex items-center space-x-2 text-xs font-mono text-gray-400">
          <span>MIN CONF:</span>
          <select
            value={minConf}
            onChange={(e) => { setMinConf(parseFloat(e.target.value)); setPage(1); }}
            className="bg-gray-950 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300"
          >
            <option value="0.0">0%</option>
            <option value="0.4">40%</option>
            <option value="0.6">60%</option>
            <option value="0.8">80%</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-gray-950 border-b border-gray-800 text-gray-400 font-mono">
            <tr>
              <th className="p-3">INCIDENT ID</th>
              <th className="p-3">CATEGORY</th>
              <th className="p-3">CLASS NAME</th>
              <th className="p-3">CONFIDENCE</th>
              <th className="p-3">SNAPSHOT</th>
              <th className="p-3">BOUNDING BOX</th>
              <th className="p-3">TIMESTAMP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800 font-mono">
            {detections.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-500">
                  NO HISTORICAL RECORDS FOUND
                </td>
              </tr>
            ) : (
              detections.map((d) => {
                const isDamage = d.category === 'road_damage';
                return (
                  <tr key={d.id} className="hover:bg-gray-850/40">
                    <td className="p-3 text-gray-400">{d.id.slice(0, 8)}...</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isDamage ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                      }`}>
                        {isDamage ? 'ROAD DAMAGE' : 'OBJECT'}
                      </span>
                    </td>
                    <td className="p-3 font-semibold text-white">{d.class_name.toUpperCase()}</td>
                    <td className="p-3 text-cyan-400 font-bold">{(d.confidence * 100).toFixed(1)}%</td>
                    <td className="p-3">
                      {d.snapshot_path ? (
                        <a href={d.snapshot_path} target="_blank" rel="noreferrer" className="inline-flex items-center text-cyan-400 hover:text-cyan-300">
                          <img src={d.snapshot_path} alt="incident" className="w-8 h-8 rounded border border-gray-700 object-cover mr-1.5" />
                          <span>View</span>
                        </a>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="p-3 text-gray-400">[{d.bbox.join(', ')}]</td>
                    <td className="p-3 text-gray-300">{new Date(d.timestamp * 1000).toLocaleString()}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Pagination Bar */}
        <div className="p-3 border-t border-gray-800 bg-gray-950 flex items-center justify-between text-xs font-mono text-gray-400">
          <span>Total Records: {totalRecords}</span>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded bg-gray-800 text-gray-300 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span>Page {page} of {Math.max(1, Math.ceil(totalRecords / 15))}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(totalRecords / 15)}
              className="p-1.5 rounded bg-gray-800 text-gray-300 disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
