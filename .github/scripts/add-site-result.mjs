import { readFileSync, writeFileSync } from 'node:fs'

export function resultPath() {
  return process.env.ADD_SITE_RESULT_PATH || '/tmp/add-site-result.json'
}

export function siteFromUrl(raw) {
  const url = (raw || '').trim()
  let parsed
  try {
    parsed = new URL(url)
  } catch {
    return null
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null
  if (!parsed.hostname) return null
  const host = parsed.hostname.replace(/^www\./i, '').toLowerCase()
  return { url, host, branch: branchForHost(host) }
}

export function branchForHost(host) {
  const slug = host.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase() || 'site'
  return `site/${slug}`.slice(0, 80)
}

export function writeResult(payload) {
  writeFileSync(resultPath(), JSON.stringify(payload))
}

export function readResult() {
  try {
    return JSON.parse(readFileSync(resultPath(), 'utf8'))
  } catch {
    return null
  }
}

export function compactSummary(value) {
  const text = typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value)
  const compact = text.replace(/\r/g, '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
  if (compact.length <= 1200) return compact
  return `${compact.slice(0, 1199).trimEnd()}…`
}

export function resultMessage({ host, url, status, summary, pullRequest, runUrl }) {
  const site = host || 'the recipe website'
  const failed = status !== 'finished'
  const lines = []
  if (failed) lines.push(`Add-site failed for ${site}.`)
  else if (pullRequest?.url) lines.push(`Add-site finished for ${site}.`)
  else lines.push(`Add-site finished for ${site} with no pull request.`)
  if (url) lines.push(url)
  if (pullRequest?.url) {
    const label = pullRequest.number ? `Pull request #${pullRequest.number}` : 'Pull request'
    lines.push(`${label}: ${pullRequest.url}`)
  }
  if (failed && runUrl) lines.push(runUrl)
  const text = compactSummary(summary)
  if (text) {
    lines.push('')
    lines.push(text)
  } else if (failed) {
    lines.push('')
    lines.push('The workflow did not record a result.')
  }
  return lines.join('\n')
}
