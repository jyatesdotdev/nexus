import { Cloud, Droplets, Wind, Thermometer } from 'lucide-react'
import type { WeatherForecastData } from '../types'

/**
 * EDUCATIONAL NOTE: Generative UI (Structured Components)
 * WHY: Traditional LLM interfaces only return text. Generative UI allows
 *      the agent to return a specific data schema that the frontend
 *      intercepts to render a bespoke, interactive, and beautiful component.
 * HOW: This component takes a raw 'weather_forecast' object and maps it
 *      to a rich visual layout using Tailwind CSS and Lucide icons. It reuses
 *      the shared WeatherForecastData shape from types.ts (the single source
 *      of the payload contract) rather than redeclaring the fields here.
 */

interface WeatherWidgetProps {
  data: WeatherForecastData
}

export function WeatherWidget({ data }: WeatherWidgetProps) {
  return (
    <div className="mt-4 p-6 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-600/10 border border-indigo-500/20 shadow-sm animate-in zoom-in-95 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        {/* Left: City & Condition */}
        <div className="space-y-1">
          <div className="text-[10px] uppercase tracking-widest font-black text-indigo-500 dark:text-indigo-400">
            Current Weather
          </div>
          <h3 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            {data.city}
          </h3>
          <div className="flex items-center gap-2 text-neutral-600 dark:text-neutral-400 font-medium">
            <Cloud className="w-4 h-4" />
            {data.description || 'N/A'}
          </div>
        </div>

        {/* Center: Temperature */}
        <div className="flex items-center gap-4 bg-white/50 dark:bg-neutral-900/50 p-4 rounded-xl backdrop-blur-sm border border-white/20">
          <Thermometer className="w-8 h-8 text-indigo-500" />
          <div className="flex flex-col">
             <span className="text-3xl font-black text-neutral-900 dark:text-neutral-100 leading-none">
               {data.temp_f}°F
             </span>
             <span className="text-sm text-neutral-500 font-medium">
               ({data.temp_c}°C)
             </span>
          </div>
        </div>

        {/* Right: Stats */}
        <div className="flex gap-8">
          <div className="flex flex-col items-center gap-1">
            <Droplets className="w-5 h-5 text-blue-500" />
            <span className="text-xs font-black text-neutral-900 dark:text-neutral-100 uppercase tracking-tighter">
              {data.humidity}%
            </span>
            <span className="text-[8px] uppercase tracking-widest text-neutral-500 font-bold">Humidity</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <Wind className="w-5 h-5 text-teal-500" />
            <span className="text-xs font-black text-neutral-900 dark:text-neutral-100 uppercase tracking-tighter">
              {data.wind_speed} <span className="text-[10px]">km/h</span>
            </span>
            <span className="text-[8px] uppercase tracking-widest text-neutral-500 font-bold">Wind</span>
          </div>
        </div>
      </div>
    </div>
  )
}
