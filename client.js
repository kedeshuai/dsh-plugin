// whitebox-testing — browser (client) half.
// Lazy-CJS bundle protocol (window.__ModuleLoader__.load with a factory
// returning cordis-plugin exports), same stance as @liustack/modlens: no
// build step, no imports of dsh client packages. React and the DSH UI
// primitives come from the factory's require; everything else is plain DOM
// styled with DSH CSS variables.
window.__ModuleLoader__.load({
  id: 'dsh-plugin-whitebox-testing',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports
    var react = require('react')
    var h = react.createElement
    var useState = react.useState
    var useEffect = react.useEffect

    var ROUTE = '/whitebox/config'

    var TEXT = {
      title: '白盒测试配置',
      subtitle: 'White-box Testing Settings',
      workspace: '工作区目录（存放 whitebox.config.json 的项目根）',
      testRoot: '测试工程目录（默认 whitebox-test）',
      sourceRoot: '被测源码根目录（必填，相对工作区或绝对路径）',
      includeDirs: '附加头文件目录（逗号分隔）',
      sourceTag: '覆盖率源过滤标记（留空取源码根末段）',
      gcc: 'GCC 路径（留空自动探测）',
      gcov: 'GCOV 路径（留空自动探测）',
      minLine: '行覆盖率门禁 (%)',
      minBranch: '分支覆盖率门禁 (%)',
      reload: '重新读取',
      save: '保存',
      openFile: '打开配置文件',
      close: '关闭',
      saving: '保存中…',
      loading: '读取中…',
      saved: '已保存到 whitebox.config.json',
      loaded: '已读取当前配置',
      reloaded: '已重新读取',
      opened: '已请求系统编辑器打开配置文件',
      needWorkspace: '请先填写工作区目录',
      needSourceRoot: '请填写被测源码根目录',
      routeOff: '宿主路由不可用：请在 Web 面板下运行 DSH，并确认插件已安装激活（可尝试在插件管理里重装本插件）',
      fetchFail: '请求失败：',
    }

    function row (label, control) {
      return h('div', { style: { marginBottom: 10 } },
        h('div', {
          style: {
            fontSize: 12, lineHeight: '18px', marginBottom: 4,
            color: 'var(--dsw-alias-label-secondary, #666)',
          },
        }, label),
        control)
    }

    var inputStyle = {
      width: '100%', boxSizing: 'border-box', padding: '6px 8px',
      fontSize: 13, borderRadius: 6,
      border: '1px solid var(--dsw-alias-border-l2, #d9d9d9)',
      background: 'var(--dsw-alias-bg-layer-3, #fff)',
      color: 'var(--dsw-alias-label-primary, #191919)',
    }

    function textInput (value, onChange, placeholder) {
      return h('input', {
        type: 'text', value: value, placeholder: placeholder || '',
        spellCheck: false,
        style: inputStyle,
        onChange: (e) => onChange(e.target.value),
      })
    }

    function normalize (form) {
      var cfg = {}
      cfg.test_root = form.test_root.trim() || 'whitebox-test'
      if (form.source_root.trim()) cfg.source_root = form.source_root.trim()
      var inc = form.include_dirs.split(',').map((s) => s.trim()).filter(Boolean)
      if (inc.length) cfg.include_dirs = inc
      if (form.source_tag.trim()) cfg.source_tag = form.source_tag.trim()
      if (form.gcc.trim()) cfg.gcc = form.gcc.trim()
      if (form.gcov.trim()) cfg.gcov = form.gcov.trim()
      var ml = parseFloat(form.min_line)
      if (!isNaN(ml)) cfg.min_line = ml
      var mb = parseFloat(form.min_branch)
      if (!isNaN(mb)) cfg.min_branch = mb
      return cfg
    }

    function toForm (config) {
      return {
        test_root: String(config.test_root || 'whitebox-test'),
        source_root: String(config.source_root || ''),
        include_dirs: Array.isArray(config.include_dirs) ? config.include_dirs.join(', ') : '',
        source_tag: String(config.source_tag || ''),
        gcc: String(config.gcc || ''),
        gcov: String(config.gcov || ''),
        min_line: config.min_line !== undefined ? String(config.min_line) : '85',
        min_branch: config.min_branch !== undefined ? String(config.min_branch) : '80',
      }
    }

    function ConfigPanel (props) {
      var st = useState({
        workspace: '', form: toForm({}), note: TEXT.loading, busy: true,
        routeOk: true,
      })
      var state = st[0]
      var set = st[1]

      function patch (p) {
        set(function (prev) {
          var next = {}
          for (var k in prev) next[k] = prev[k]
          for (var k2 in p) next[k2] = p[k2]
          return next
        })
      }

      function patchForm (key, value) {
        set(function (prev) {
          var form = {}
          for (var k in prev.form) form[k] = prev.form[k]
          form[key] = value
          var next = {}
          for (var k2 in prev) next[k2] = prev[k2]
          next.form = form
          return next
        })
      }

      function load (msg) {
        patch({ busy: true, note: TEXT.loading })
        fetch(ROUTE)
          .then((r) => r.json().then((body) => ({ status: r.status, body: body })))
          .then((res) => {
            if (res.status === 403 || res.status === 404) {
              patch({ busy: false, routeOk: false, note: TEXT.routeOff })
              return
            }
            patch({
              busy: false, routeOk: true,
              workspace: res.body.workspace || '',
              form: toForm(res.body.config || {}),
              note: msg || TEXT.loaded,
            })
          })
          .catch((e) => patch({ busy: false, routeOk: false, note: TEXT.fetchFail + String(e) }))
      }

      useEffect(() => { load(TEXT.loaded) }, [])

      function save () {
        if (!state.workspace.trim()) { patch({ note: TEXT.needWorkspace }); return }
        if (!state.form.source_root.trim()) { patch({ note: TEXT.needSourceRoot }); return }
        patch({ busy: true, note: TEXT.saving })
        fetch(ROUTE, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ workspace: state.workspace.trim(), config: normalize(state.form) }),
        })
          .then((r) => r.json().then((body) => ({ status: r.status, body: body })))
          .then((res) => {
            if (res.status >= 400) throw new Error(res.body && res.body.error || res.status)
            patch({ busy: false, note: TEXT.saved })
          })
          .catch((e) => patch({ busy: false, note: TEXT.fetchFail + String(e) }))
      }

      function openFile () {
        if (!state.workspace.trim()) { patch({ note: TEXT.needWorkspace }); return }
        fetch(ROUTE, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ workspace: state.workspace.trim(), open: true }),
        })
          .then((r) => r.json().then((body) => ({ status: r.status, body: body })))
          .then((res) => {
            if (res.status >= 400) throw new Error(res.body && res.body.error || res.status)
            patch({ note: TEXT.opened })
          })
          .catch((e) => patch({ note: TEXT.fetchFail + String(e) }))
      }

      var f = state.form
      return h('div', {
        style: {
          maxHeight: '70vh', overflowY: 'auto', padding: 16,
        },
      },
      h('div', {
        style: {
          fontSize: 12, lineHeight: '18px', marginBottom: 12, wordBreak: 'break-all',
          color: 'var(--dsw-alias-label-tertiary, #999)',
        },
      }, 'wb.py run / gate 将按此配置定位被测源码与工具链；配置写入 <工作区>/whitebox.config.json。'),
      row(TEXT.workspace, textInput(state.workspace, (v) => patch({ workspace: v }), '例如 D:\\Work\\white-test')),
      row(TEXT.testRoot, textInput(f.test_root, (v) => patchForm('test_root', v), 'whitebox-test')),
      row(TEXT.sourceRoot, textInput(f.source_root, (v) => patchForm('source_root', v), 'path/to/MainProject/source')),
      row(TEXT.includeDirs, textInput(f.include_dirs, (v) => patchForm('include_dirs', v), 'path/to/bsp, path/to/inc')),
      row(TEXT.sourceTag, textInput(f.source_tag, (v) => patchForm('source_tag', v), '默认取源码根末段')),
      row(TEXT.gcc, textInput(f.gcc, (v) => patchForm('gcc', v), 'C:/msys64/ucrt64/bin/gcc.exe')),
      row(TEXT.gcov, textInput(f.gcov, (v) => patchForm('gcov', v), 'C:/msys64/ucrt64/bin/gcov.exe')),
      h('div', { style: { display: 'flex', gap: 10 } },
        h('div', { style: { flex: 1 } }, row(TEXT.minLine, textInput(f.min_line, (v) => patchForm('min_line', v), '85'))),
        h('div', { style: { flex: 1 } }, row(TEXT.minBranch, textInput(f.min_branch, (v) => patchForm('min_branch', v), '80')))),
      h('div', {
        style: {
          fontSize: 12, lineHeight: '18px', minHeight: 18, marginBottom: 10,
          color: state.routeOk ? 'var(--dsw-alias-label-secondary, #666)' : '#c0392b',
        },
      }, state.note),
      h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } },
        h('button', { type: 'button', onClick: save, disabled: state.busy, style: primaryBtn }, TEXT.save),
        h('button', { type: 'button', onClick: () => load(TEXT.reloaded), disabled: state.busy, style: ghostBtn }, TEXT.reload),
        h('button', { type: 'button', onClick: openFile, disabled: state.busy, style: ghostBtn }, TEXT.openFile),
        props && props.onClose
          ? h('button', { type: 'button', onClick: props.onClose, style: ghostBtn }, TEXT.close)
          : null))
    }

    var primaryBtn = {
      padding: '6px 14px', fontSize: 13, borderRadius: 6, cursor: 'pointer',
      border: '1px solid transparent',
      background: 'var(--dsw-alias-brand-primary, #2b5fd9)', color: '#fff',
    }
    var ghostBtn = {
      padding: '6px 14px', fontSize: 13, borderRadius: 6, cursor: 'pointer',
      border: '1px solid var(--dsw-alias-border-l2, #d9d9d9)',
      background: 'var(--dsw-alias-bg-layer-2, transparent)',
      color: 'var(--dsw-alias-label-primary, #191919)',
    }

    // The sidebar-foot action cell: an icon button beside Settings that opens
    // the settings panel as a centered modal. The seat only hands us column
    // state (wide), so open/close is ours to manage.
    function WhiteboxEntry (props) {
      var st = useState(false)
      var open = st[0]
      var setOpen = st[1]
      var wide = props && props.wide
      return h(react.Fragment, null,
        h('button', {
          type: 'button',
          title: TEXT.title,
          'aria-label': TEXT.title,
          onClick: () => setOpen(!open),
          style: {
            display: 'flex', alignItems: 'center', gap: 8, width: '100%',
            padding: wide ? '6px 10px' : '6px', cursor: 'pointer',
            border: '1px solid transparent', borderRadius: 8,
            background: open ? 'var(--dsw-alias-bg-layer-3, rgba(127,127,127,.15))' : 'transparent',
            color: 'var(--dsw-alias-label-secondary, #666)',
          },
        },
        h('svg', {
          viewBox: '0 0 24 24', width: 20, height: 20, fill: 'none',
          stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round',
          'stroke-linejoin': 'round', 'aria-hidden': 'true',
          style: { flexShrink: 0 },
        },
        h('rect', { x: 3, y: 3, width: 18, height: 18, rx: 3 }),
        h('path', { d: 'M7 9l2 2 4-4' }),
        h('path', { d: 'M7 16l2 2 4-4' }),
        h('path', { d: 'M15 9h3' }),
        h('path', { d: 'M15 16h3' })),
        wide ? h('span', {
          style: {
            flex: 1, textAlign: 'left', fontSize: 13,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          },
        }, TEXT.title) : null),
        open
          ? h('div', {
            style: {
              position: 'fixed', inset: 0, zIndex: 1000,
              background: 'rgba(0,0,0,.35)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            },
            onClick: (e) => { if (e.target === e.currentTarget) setOpen(false) },
          },
          h('div', {
            style: {
              width: 460, maxWidth: '90vw', borderRadius: 12,
              background: 'var(--dsw-alias-bg-layer-2, #fff)',
              border: '1px solid var(--dsw-alias-border-l2, #d9d9d9)',
              boxShadow: '0 12px 40px rgba(0,0,0,.25)',
            },
          },
          h('div', {
            style: {
              padding: '14px 16px 0',
              borderBottom: '1px solid var(--dsw-alias-border-l2, #eee)',
            },
          },
          h('div', {
            style: {
              fontSize: 15, fontWeight: 600, paddingBottom: 10,
              color: 'var(--dsw-alias-label-primary, #191919)',
            },
          }, TEXT.title, h('span', {
            style: {
              marginLeft: 8, fontSize: 11, fontWeight: 400,
              color: 'var(--dsw-alias-label-tertiary, #999)',
            },
          }, TEXT.subtitle))),
          h(ConfigPanel, { onClose: () => setOpen(false) })))
          : null)
    }

    function apply (ctx) {
      // Reaching for an undeclared service throws in cordis ("service not
      // available"), and a throwing entry takes the WHOLE web boot down
      // ("web boot: 1 entry did not activate"). So: register through a
      // scoped ctx.inject(['slots']) like @liustack/modlens does, and never
      // let anything inside apply escape to the activator.
      if (typeof ctx.inject !== 'function') return
      try {
        ctx.inject(['slots'], (scope) => {
          var slots = scope && scope.slots
          if (!slots || typeof slots.inject !== 'function' || typeof slots.register !== 'function') return
          try {
            // Sidebar foot cell beside Settings (official example shape
            // from the slot catalog: inject returns the register result).
            slots.inject('sidebar.footer.action', () => slots.register({
              name: 'sidebar.footer.action',
              id: 'whitebox-testing',
              order: 120,
              label: TEXT.title,
            }, WhiteboxEntry))
            // Same form also lands on the Plugins page config tab (key =
            // package name, dsh 0.1.7+), mirroring the modlens registration.
            slots.inject('plugins.bundle.config', function * () {
              yield slots.register({
                name: 'plugins.bundle.config',
                key: 'dsh-plugin-whitebox-testing',
              }, ConfigPanel)
            })
          } catch (error) {
            console.error('[whitebox-testing] slot registration skipped: ' + error)
          }
        })
      } catch (error) {
        console.error('[whitebox-testing] apply skipped: ' + error)
      }
    }

    exports.apply = function (ctx) {
      try {
        apply(ctx)
      } catch (error) {
        console.error('[whitebox-testing] apply crashed: ' + error)
      }
    }
    exports.inject = []
    return module.exports
  },
})
