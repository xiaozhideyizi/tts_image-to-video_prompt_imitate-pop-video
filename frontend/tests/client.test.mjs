import assert from 'node:assert/strict'
import test from 'node:test'
import { build } from 'esbuild'

async function loadClient(url = '') {
  const values = new Map([['token', 'saved-token'], ['user', '{"id":1}']])
  globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    removeItem: key => values.delete(key),
  }
  globalThis.window = { location: { href: '/login' } }
  const result = await build({
    stdin: {
      contents: "export { default } from './src/api/client.js'; export { promptApi } from './src/api/index.js'",
      resolveDir: process.cwd(),
    },
    bundle: true, write: false,
    format: 'esm', platform: 'browser',
    define: { 'import.meta.env.VITE_API_URL': JSON.stringify(url) },
  })
  const source = result.outputFiles[0].text + `\n// ${Math.random()}`
  const { default: api, promptApi } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
  return { api, promptApi, values }
}

test('后端地址支持域名、/api 和同源代理', async () => {
  for (const [url, expected] of [
    ['', '/api'], ['https://example.com', 'https://example.com/api'],
    ['https://example.com/api/', 'https://example.com/api'],
    ['  https://example.com/  ', 'https://example.com/api'],
  ]) {
    const { api } = await loadClient(url)
    assert.equal(api.defaults.baseURL, expected)
  }
})

test('登录密码错误保留页面、错误信息及已有凭据', async () => {
  const { api, values } = await loadClient()
  const errorResponse = { status: 401, data: { detail: '邮箱或密码错误' } }
  api.defaults.adapter = config => Promise.reject({ config, response: errorResponse })
  await assert.rejects(api.post('/auth/token'), error => error.response === errorResponse)
  assert.equal(window.location.href, '/login')
  assert.equal(values.get('token'), 'saved-token')
})

test('受保护接口的过期凭据会清理并跳转登录', async () => {
  const { api, values } = await loadClient()
  window.location.href = '/history'
  api.defaults.adapter = config => Promise.reject({ config, response: { status: 401 } })
  await assert.rejects(api.get('/prompts/history'))
  assert.equal(values.size, 0)
  assert.equal(window.location.href, '/login')
})

test('后端不可用时保留登录凭据', async () => {
  const { api, values } = await loadClient()
  api.defaults.adapter = config => Promise.reject({ config, response: { status: 503 } })
  await assert.rejects(api.get('/prompts/history'))
  assert.equal(values.get('token'), 'saved-token')
})

test('AI 状态检查和生成请求使用新后端配置', async () => {
  const { api, promptApi } = await loadClient('https://new-backend.example.com')
  const calls = []
  api.defaults.adapter = async config => {
    calls.push(config)
    return { status: 200, data: {}, headers: {}, config }
  }
  await promptApi.checkAI()
  await promptApi.generate(new FormData())
  assert.equal(calls[0].baseURL, 'https://new-backend.example.com/api')
  assert.equal(calls[0].url, '/prompts/check-ai')
  assert.equal(calls[1].baseURL, calls[0].baseURL)
  assert.equal(calls[1].timeout, 240000)
})
