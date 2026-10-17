import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import process from 'node:process'

function git(args) {
  return execFileSync('git', args, { encoding: 'utf8' }).trim()
}

function gh(args) {
  return execFileSync('gh', args, { encoding: 'utf8' }).trim()
}

function prComments(number) {
  const raw = gh(['pr', 'view', String(number), '--json', 'comments'])
  return JSON.parse(raw).comments || []
}

async function comment(number, body) {
  const directory = await mkdtemp(join(tmpdir(), 'upstream-sync-'))
  const bodyPath = join(directory, 'comment.md')
  await writeFile(bodyPath, body)
  execFileSync('gh', ['pr', 'comment', String(number), '--body-file', bodyPath], {
    stdio: 'inherit',
  })
}

function cursorMaxAttempts() {
  const attempts = Number.parseInt(process.env.CURSOR_MAX_ATTEMPTS || '3', 10)
  return Number.isFinite(attempts) && attempts > 0 ? attempts : 3
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isRetryableCursorError(error) {
  const message = `${error?.message || ''} ${error?.cause?.message || ''}`
  return Boolean(
    error?.isRetryable ||
      error?.code === 14 ||
      error?.code === 'ETIMEDOUT' ||
      error?.cause?.code === 'ETIMEDOUT' ||
      /ETIMEDOUT|ECONNRESET|EAI_AGAIN|ENOTFOUND|unavailable/i.test(message)
  )
}

async function promptWithRetry(Agent, prompt, options) {
  const maxAttempts = cursorMaxAttempts()
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await Agent.prompt(prompt, options)
    } catch (error) {
      if (!isRetryableCursorError(error) || attempt === maxAttempts) {
        throw error
      }
      const delayMs = Math.min(15_000 * attempt, 60_000)
      console.error(
        `Cursor report attempt ${attempt}/${maxAttempts} failed; retrying in ${delayMs / 1000}s.`
      )
      console.error(error)
      await sleep(delayMs)
    }
  }
  return undefined
}

async function ensureReport(prNumber, report) {
  const bodies = prComments(prNumber).map((comment) => comment.body || '')
  if (!bodies.some((body) => body.includes('## Upstream sync report'))) {
    await comment(prNumber, report)
  }
  const afterReport = prComments(prNumber).map((comment) => comment.body || '')
  if (!afterReport.some((body) => body.trim() === 'bugbot run')) {
    await comment(prNumber, 'bugbot run')
  }
}

async function main() {
  const prNumber = process.env.PR_NUMBER
  const prUrl = process.env.PR_URL || ''
  if (!prNumber) {
    throw new Error('PR_NUMBER is required')
  }

  const summary = JSON.parse(await readFile(process.env.SUMMARY_PATH, 'utf8'))
  const report = await readFile(process.env.REPORT_PATH, 'utf8')
  const template = await readFile('.github/prompts/upstream-sync-report.md', 'utf8')
  const blockReasons = (summary.block_reasons || []).join(', ') || 'none'
  const prompt = [
    template
      .replaceAll('{{REPORT_MARKDOWN}}', report)
      .replaceAll('{{PR_URL}}', prUrl)
      .replaceAll('{{MINIMUM_VERDICT}}', summary.minimum_verdict || '')
      .replaceAll('{{BLOCK_REASONS}}', blockReasons),
    [
      'Automation guardrails:',
      '- Do not merge, deploy, promote, roll back, or push to main.',
      '- Do not rebase onto upstream.',
      `- Current branch: ${git(['rev-parse', '--abbrev-ref', 'HEAD'])}`,
      `- Pull request: ${prUrl}`,
    ].join('\n'),
  ].join('\n\n')

  if (!process.env.CURSOR_API_KEY) {
    console.error(
      'CURSOR_API_KEY is not set; posting the deterministic report without the Cursor agent.'
    )
    await ensureReport(prNumber, report)
    process.exitCode = 1
    return
  }

  let finished = false
  try {
    const { Agent } = await import('@cursor/sdk')
    const modelId = process.env.CURSOR_MODEL || 'auto'
    console.log(`Running upstream sync report with Cursor model: ${modelId}`)
    const result = await promptWithRetry(Agent, prompt, {
      apiKey: process.env.CURSOR_API_KEY,
      model: { id: modelId },
      local: { cwd: process.cwd(), settingSources: ['project'] },
    })
    console.log(result?.status)
    console.log(result?.result || '')
    finished = result?.status === 'finished'
    if (!finished) {
      process.exitCode = 1
    }
  } catch (error) {
    console.error(error)
    process.exitCode = 1
  }

  await ensureReport(prNumber, report)
  if (!finished) {
    process.exitCode = 1
  }
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
