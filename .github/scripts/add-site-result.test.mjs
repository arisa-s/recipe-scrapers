import assert from 'node:assert/strict'
import test from 'node:test'
import { compactSummary, resultMessage, siteFromUrl } from './add-site-result.mjs'

test('maps a recipe URL to the site branch', () => {
  assert.deepEqual(siteFromUrl('https://www.example.com/recipes/pasta'), {
    url: 'https://www.example.com/recipes/pasta',
    host: 'example.com',
    branch: 'site/example-com',
  })
  assert.equal(siteFromUrl('javascript:alert(1)'), null)
})

test('includes the pull request link when one was opened', () => {
  const text = resultMessage({
    host: 'example.com',
    url: 'https://example.com/recipes/pasta',
    status: 'finished',
    summary: 'Added a fallback scraper.',
    pullRequest: { number: 12, url: 'https://github.com/arisa-s/recipe-scrapers/pull/12' },
  })
  assert.match(text, /^Add-site finished for example.com\./)
  assert.match(text, /Pull request #12: https:\/\/github.com\/arisa-s\/recipe-scrapers\/pull\/12/)
  assert.match(text, /Added a fallback scraper\./)
})

test('says when the run finished without a pull request', () => {
  const text = resultMessage({
    host: 'example.com',
    url: 'https://example.com/recipes/pasta',
    status: 'finished',
    summary: 'wont_fix login wall',
    pullRequest: null,
  })
  assert.match(text, /no pull request/)
  assert.doesNotMatch(text, /Pull request/)
  assert.match(text, /wont_fix login wall/)
})

test('includes the workflow run when the action fails', () => {
  const text = resultMessage({
    host: 'example.com',
    status: 'error',
    summary: '',
    runUrl: 'https://github.com/arisa-s/recipe-scrapers/actions/runs/9',
  })
  assert.match(text, /Add-site failed for example.com\./)
  assert.match(text, /actions\/runs\/9/)
  assert.match(text, /did not record a result/)
})

test('keeps a pinned summary short', () => {
  const text = compactSummary(`  ${'a'.repeat(1500)}  `)
  assert.equal(text.length, 1200)
  assert.ok(text.endsWith('…'))
})
