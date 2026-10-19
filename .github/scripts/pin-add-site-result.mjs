import { execFileSync } from 'node:child_process'
import process from 'node:process'
import { readResult, resultMessage, siteFromUrl } from './add-site-result.mjs'

function pullRequestFor(branch) {
  if (!branch) return null
  try {
    const raw = execFileSync(
      'gh',
      ['pr', 'list', '--head', branch, '--state', 'open', '--limit', '1', '--json', 'url,number,title'],
      { encoding: 'utf8' }
    )
    const list = JSON.parse(raw)
    return list[0] || null
  } catch {
    console.error('Could not look up a pull request.')
    return null
  }
}

function runUrl() {
  const repo = process.env.GITHUB_REPOSITORY
  const id = process.env.GITHUB_RUN_ID
  if (!repo || !id) return ''
  return `https://github.com/${repo}/actions/runs/${id}`
}

async function slack(method, token, body) {
  const response = await fetch(`https://slack.com/api/${method}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json; charset=utf-8',
    },
    body: JSON.stringify(body),
  })
  const payload = await response.json().catch(() => ({}))
  if (!payload.ok) {
    throw new Error(`Slack ${method} failed: ${payload.error || response.status}`)
  }
  return payload
}

async function main() {
  const token = process.env.SLACK_BOT_TOKEN || ''
  const channel = process.env.SLACK_CHANNEL_ID || ''
  if (!token || !channel) {
    throw new Error('Set secret SLACK_BOT_TOKEN and variable SLACK_CHANNEL_ID. The bot needs chat:write and pins:write, and it must be in that channel.')
  }

  const recorded = readResult()
  const parsed = siteFromUrl(process.env.RECIPE_URL)
  const branch = recorded?.branch || parsed?.branch
  const pullRequest = pullRequestFor(branch)
  const text = resultMessage({
    host: recorded?.host || parsed?.host,
    url: recorded?.url || parsed?.url,
    status: recorded?.status,
    summary: recorded?.summary,
    pullRequest,
    runUrl: runUrl(),
  })

  const posted = await slack('chat.postMessage', token, { channel, text, unfurl_links: true })
  try {
    await slack('pins.add', token, { channel, timestamp: posted.ts })
  } catch (error) {
    if (!String(error.message).includes('already_pinned')) throw error
  }
  console.log(pullRequest?.url ? `Pinned add-site result with ${pullRequest.url}` : 'Pinned add-site result with no pull request.')
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : 'Could not pin the add-site result.')
  process.exit(1)
})
