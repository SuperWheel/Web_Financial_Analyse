import { describe, expect, it } from 'vitest'
import {
  buildCoverageRows,
  coverageTagType,
  formatMoney,
  formatPeriodLabels,
  overallCoveragePct,
  statementKindLabel,
  unmappedReasonLabel,
} from './importCoverage'

describe('importCoverage', () => {
  it('buildCoverageRows maps core hit rates to percent', () => {
    const rows = buildCoverageRows({
      balance: { core_total: 10, core_hit: 8, mapped_fields: 20, coverage: 0.8 },
      income: { core_total: 8, core_hit: 4, mapped_fields: 10, coverage: 0.5 },
      cashflow: { core_total: 6, core_hit: 6, mapped_fields: 12, coverage: 1 },
    })
    expect(rows).toHaveLength(3)
    expect(rows[0]).toMatchObject({ kind: 'balance', coreHit: 8, coreTotal: 10, pct: 80 })
    expect(rows[1].pct).toBe(50)
    expect(rows[2].pct).toBe(100)
  })

  it('overallCoveragePct is weighted by core_total', () => {
    const pct = overallCoveragePct({
      balance: { core_total: 10, core_hit: 8 },
      income: { core_total: 8, core_hit: 3 },
      cashflow: { core_total: 6, core_hit: 6 },
    })
    // (8+3+6)/(10+8+6) = 17/24 ≈ 71%
    expect(pct).toBe(71)
  })

  it('overallCoveragePct returns null without core totals', () => {
    expect(overallCoveragePct({})).toBeNull()
    expect(overallCoveragePct(null)).toBeNull()
  })

  it('coverageTagType thresholds', () => {
    expect(coverageTagType(90)).toBe('success')
    expect(coverageTagType(80)).toBe('success')
    expect(coverageTagType(50)).toBe('warning')
    expect(coverageTagType(10)).toBe('danger')
    expect(coverageTagType(0)).toBe('info')
  })

  it('labels and money formatters', () => {
    expect(unmappedReasonLabel('ambiguous')).toBe('多科目歧义')
    expect(unmappedReasonLabel('unknown_x')).toBe('unknown_x')
    expect(unmappedReasonLabel()).toBe('—')
    expect(statementKindLabel('income')).toBe('利润表')
    expect(statementKindLabel('other')).toBe('other')
    expect(formatMoney(null)).toBe('—')
    expect(formatMoney(1234.5)).toMatch(/1,234\.50/)
    expect(formatPeriodLabels([{ label: '2023 年报' }, { label: '2024 年报' }])).toBe(
      '2023 年报、2024 年报'
    )
    expect(formatPeriodLabels([])).toBe('—')
  })
})
