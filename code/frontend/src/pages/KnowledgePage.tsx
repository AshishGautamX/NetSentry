import React, { useEffect, useState } from "react";
import {
  Database,
  Search,
  ToggleLeft,
  ToggleRight,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { apiClient } from "../api/client";
import { LearnedMapping } from "../types";
import { LoadingSkeleton } from "../components/common/LoadingSkeleton";
import { EmptyState } from "../components/common/EmptyState";

export const KnowledgePage: React.FC = () => {
  const [mappings, setMappings] = useState<LearnedMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedVendor, setSelectedVendor] = useState("ALL");

  useEffect(() => {
    fetchKnowledge();
  }, []);

  const fetchKnowledge = async () => {
    try {
      setLoading(true);
      const data = await apiClient.listKnowledgeBase();
      setMappings(data);
    } catch (err) {
      console.error("Failed to fetch knowledge base", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const updated = await apiClient.toggleKnowledgeMapping(id);
      setMappings((prev) => prev.map((m) => (m.id === id ? updated : m)));
    } catch (err) {
      console.error("Failed to toggle mapping", err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this learned normalization rule?")) return;
    try {
      await apiClient.deleteKnowledgeMapping(id);
      setMappings((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      console.error("Failed to delete mapping", err);
    }
  };

  const vendors = Array.from(new Set(mappings.map((m) => m.vendor)));

  const filteredMappings = mappings.filter((m) => {
    if (selectedVendor !== "ALL" && m.vendor !== selectedVendor) return false;
    const term = searchTerm.toLowerCase();
    return (
      m.command_pattern.toLowerCase().includes(term) ||
      m.normalized_param.toLowerCase().includes(term) ||
      m.semantic_category.toLowerCase().includes(term) ||
      m.vendor.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Title & Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            Adaptive Knowledge Base & Canonical Mappings
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Structured repository of multi-vendor command patterns and normalized parameters across all supported platforms.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Box */}
          <div className="relative w-56">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search pattern, param, vendor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-slate-200 text-xs text-slate-800 pl-8 pr-3 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono"
            />
          </div>

          {/* Vendor Filter */}
          <select
            value={selectedVendor}
            onChange={(e) => setSelectedVendor(e.target.value)}
            className="bg-white border border-slate-200 text-xs text-slate-700 px-2.5 py-1.5 rounded-md focus:outline-none focus:border-slate-500 font-mono uppercase"
          >
            <option value="ALL">All Vendors ({vendors.length})</option>
            {vendors.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>

          <button
            onClick={fetchKnowledge}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded transition-colors"
            title="Refresh knowledge base"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Mappings Table */}
      {loading ? (
        <LoadingSkeleton type="table" rows={8} />
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-white text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Vendor</th>
                  <th className="px-4 py-2.5">Command Pattern (Regex)</th>
                  <th className="px-4 py-2.5">Normalized Canonical Parameter</th>
                  <th className="px-4 py-2.5">Domain Category</th>
                  <th className="px-4 py-2.5">Origin</th>
                  <th className="px-4 py-2.5">Evaluations</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 font-mono text-[11px]">
                {filteredMappings.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="text-[10px] uppercase bg-white text-slate-700 px-1.5 py-0.2 rounded border border-slate-200">
                        {m.vendor}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-800 max-w-sm truncate" title={m.command_pattern}>
                      {m.command_pattern}
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-slate-700 bg-white px-1 py-0.5 rounded border border-slate-200">
                        {m.normalized_param}
                      </code>
                    </td>
                    <td className="px-4 py-3 text-slate-500 font-sans">
                      {m.semantic_category}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded border ${
                          m.source === "HUMAN_TRAINING"
                            ? "bg-amber-50 text-amber-700 border-amber-800"
                            : "bg-white text-slate-500 border-slate-200"
                        }`}
                      >
                        {m.source}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {m.use_count} {m.use_count === 1 ? "hit" : "hits"}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleToggle(m.id)}
                        className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded transition-colors ${
                          m.is_active
                            ? "text-emerald-700 bg-emerald-950/40 border border-emerald-200"
                            : "text-slate-500 bg-slate-50 border border-slate-200"
                        }`}
                      >
                        {m.is_active ? (
                          <ToggleRight className="w-3.5 h-3.5" />
                        ) : (
                          <ToggleLeft className="w-3.5 h-3.5" />
                        )}
                        <span>{m.is_active ? "ACTIVE" : "DISABLED"}</span>
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {m.source === "HUMAN_TRAINING" && (
                        <button
                          onClick={() => handleDelete(m.id)}
                          className="p-1 rounded text-slate-500 hover:text-red-700 hover:bg-white transition-colors"
                          title="Delete Learned Rule"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredMappings.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center font-sans">
                      <EmptyState
                        icon={Database}
                        title="No Mappings Found"
                        description="Adjust your search query or vendor filter to view knowledge base mappings."
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
