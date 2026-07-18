import { describe, expect, it } from 'vitest'
import type { RatioHistory } from '@/api/ratio'
import { computeYoY } from './ratioInsights'

function historyFor(
  key: string,
  points: Array<{
    year: number
    value: number | null
    period_type?: 'annual' | 'quarterly'
    quarter?: number | null
  }>
): RatioHistory {
  return {
    company_id: 1,
    period_type: 'annual',
    periods: points.map((p) => ({
      year: p.year,
      period_type: p.period_type ?? 'annual',
      quarter: p.quarter ?? null,
    })),
    series: {
      [key]: {
        key,
        name: key,
        unit: 'ratio',
        points: points.map((p) => ({
          year: p.year,
          period_type: p.period_type ?? 'annual',
          quarter: p.quarter ?? null,
          value: p.value,
        })),
      },
    },
  }
}

describe('computeYoY', () => {
  it('uses the prior year relative to selected period, not global latest', () => {
    // History includes a future 2025 point; selecting 2024 must compare to 2023.
    const hist = historyFor('current_ratio', [
      { year: 2022, value: 1.0 },
      { year: 2023, value: 1.5 },
      { year: 2024, value: 1.8 },
      { year: 2025, value: 2.5 },
    ])
    const yoy = computeYoY('current_ratio', 'ratio', 1.8, hist, {
      year: 2024,
      period_type: 'annual',
      quarter: null,
    })
    expect(yoy.prev).toBe(1.5)
    expect(yoy.delta).toBeCloseTo(0.3)
    expect(yoy.previousPeriodLabel).toBe('2023 年报')
    expect(yoy.direction).toBe('up')
    expect(yoy.improved).toBe(true) // current_ratio prefers higher
  })

  it('skips missing intermediate years to the nearest earlier period', () => {
    const hist = historyFor('roe', [
      { year: 2021, value: 0.1 },
      { year: 2023, value: 0.12 }, // 2022 missing
      { year: 2024, value: 0.15 },
    ])
    const yoy = computeYoY('roe', 'percent', 0.15, hist, {
      year: 2024,
      period_type: 'annual',
    })
    expect(yoy.prev).toBe(0.12)
    expect(yoy.previousPeriodLabel).toBe('2023 年报')
  })

  it('returns empty when no earlier period exists', () => {
    const hist = historyFor('roe', [{ year: 2024, value: 0.1 }])
    const yoy = computeYoY('roe', 'percent', 0.1, hist, {
      year: 2024,
      period_type: 'annual',
    })
    expect(yoy.prev).toBeNull()
    expect(yoy.direction).toBe('na')
  })

  it('marks debt_to_equity decrease as improve (lower is better)', () => {
    const hist = historyFor('debt_to_equity', [
      { year: 2023, value: 1.2 },
      { year: 2024, value: 0.9 },
    ])
    const yoy = computeYoY('debt_to_equity', 'ratio', 0.9, hist, {
      year: 2024,
      period_type: 'annual',
    })
    expect(yoy.delta).toBeCloseTo(-0.3)
    expect(yoy.improved).toBe(true)
    expect(yoy.meaning).toBe('improve')
  })
})
