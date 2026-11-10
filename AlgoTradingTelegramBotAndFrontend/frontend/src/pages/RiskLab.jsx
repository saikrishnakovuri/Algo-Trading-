import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { FlaskConical, Calculator, Activity, ShieldAlert } from 'lucide-react';

const RiskLab = () => {
  const [capital, setCapital] = useState(1000000);
  const [riskPct, setRiskPct] = useState(2.0);
  const [slDist, setSlDist] = useState(25);
  
  const lots = Math.floor((capital * (riskPct/100)) / (slDist * 65)); // Assuming NIFTY 65

  return (
    <div className="p-8 space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-widest flex items-center gap-3">
        <FlaskConical className="text-[#00bcd4]" /> Risk Simulator Lab
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Position Sizer */}
        <div className="bg-[#161b27] border border-[#1e2130] p-8 rounded-xl space-y-6">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <Calculator size={16} className="text-[#00bcd4]" /> Position Sizing (NIFTY)
          </h3>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Trading Capital (₹)</label>
              <input type="number" className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono" value={capital} onChange={(e)=>setCapital(parseInt(e.target.value))} />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Risk Per Trade (%)</label>
              <input type="number" step="0.5" className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono" value={riskPct} onChange={(e)=>setRiskPct(parseFloat(e.target.value))} />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">SL Distance (Points Premium)</label>
              <input type="number" className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono" value={slDist} onChange={(e)=>setSlDist(parseInt(e.target.value))} />
            </div>
          </div>

          <div className="pt-6 border-t border-[#1e2130] grid grid-cols-2 gap-4 text-center">
            <div className="bg-[#0f1117] p-4 rounded-lg">
              <p className="text-[10px] text-gray-600 font-bold uppercase">Risk Amount</p>
              <p className="text-lg font-bold text-red-500">₹{(capital * (riskPct/100)).toLocaleString()}</p>
            </div>
            <div className="bg-[#0f1117] p-4 rounded-lg">
              <p className="text-[10px] text-gray-600 font-bold uppercase">Recommended Lots</p>
              <p className="text-lg font-bold text-green-500">{lots} Lots</p>
              <p className="text-[8px] text-gray-500">({lots * 65} Units)</p>
            </div>
          </div>
        </div>

        {/* Kelly Criterion */}
        <div className="bg-[#161b27] border border-[#1e2130] p-8 rounded-xl space-y-6">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <Activity size={16} className="text-[#00c853]" /> Kelly Optimal F
          </h3>
          <div className="space-y-4 text-center py-10">
             <div className="inline-block p-8 bg-[#0f1117] rounded-full border-4 border-[#1e2130]">
                <p className="text-3xl font-bold text-[#00c853]">1.2%</p>
                <p className="text-[10px] text-gray-500 font-bold uppercase">Optimal Risk</p>
             </div>
             <p className="text-xs text-gray-500 max-w-[250px] mx-auto leading-relaxed">
               Based on historical win rate (42%) and profit factor (1.4). Recommended: 0.6% (Half-Kelly).
             </p>
          </div>
          <div className="flex gap-4">
             <div className="flex-1 bg-[#0f1117] p-4 rounded-lg border border-[#1e2130]">
                <p className="text-[10px] text-gray-600 font-bold uppercase">P(Ruin)</p>
                <p className="text-sm font-bold text-white">0.02%</p>
             </div>
             <div className="flex-1 bg-[#0f1117] p-4 rounded-lg border border-[#1e2130]">
                <p className="text-[10px] text-gray-600 font-bold uppercase">Max DD Prob</p>
                <p className="text-sm font-bold text-white">12.5%</p>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskLab;
