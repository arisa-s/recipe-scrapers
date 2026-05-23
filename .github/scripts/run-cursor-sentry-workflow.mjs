import { readFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import process from 'node:process'
import { Agent } from '@cursor/sdk'

const PROMPTS = {
  investigate: '.github/prompts/sentry-investigate.md',
  dedupe: '.github/prompts/sentry-dedupe.md',
  'fix-draft': '.github/prompts/sentry-fix-draft.md',
  verify: '.github/prompts/sentry-verify.md',
}

function input(name, fallback = '') {
  return process.env[`INPUT_${name.toUpperCase().replaceAll('-', '_')}`] || fallback
}

function git(args) {
  return execFileSync('git', args, { encoding: 'utf8' }).trim()
}

function ensureSafeMode(mode) {
  if (!['investigate', 'dedupe', 'fix-draft', 'verify'].includes(mode)) {
    throw new Error(`Unsupported workflow mode: ${mode}`)
  }
}

async function main() {
  const mode = input('mode', 'investigate')
  ensureSafeMode(mode)

  const issue = input('issue-url') || input('sentry-url') || process.env.GITHUB_EVENT_ISSUE_HTML_URL || ''
  const promptPath = PROMPTS[mode]
  const template = await readFile(promptPath, 'utf8')
  const prompt = template
    .replaceAll('{{SENTRY_URL_OR_ID}}', issue)
    .replaceAll('{{GITHUB_ISSUE_OR_SENTRY_URL}}', issue)

  const branch = git(['rev-parse', '--abbrev-ref', 'HEAD'])
  const status = git(['status', '--porcelain'])
  if (mode === 'fix-draft' && status) {
    throw new Error('Refusing to run fix-draft with a dirty working tree.')
  }

  const guardrails = [
    'Automation guardrails:',
    '- Do not merge, deploy, promote, roll back, pause services, restore databases, run production migrations, or change production config.',
    '- Do not use Sentry Seer.',
    '- Use Railway, Expo, and Supabase MCP tools read-only unless a human explicitly approved a specific write action.',
    '- Create draft PRs only. Human review, merge, and deploy are required.',
    `- Current branch: ${branch}`,
  ].join('\n')

  const result = await Agent.prompt(`${prompt}\n\n${guardrails}`, {
    apiKey: process.env.CURSOR_API_KEY,
    model: { id: process.env.CURSOR_MODEL || 'auto' },
    local: { cwd: process.cwd() },
  })

  console.log(result.status)
  console.log(result.result || '')
  if (result.status !== 'finished') {
    process.exitCode = 2
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
