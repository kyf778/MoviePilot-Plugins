import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,openBlock:_openBlock,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "pa-4" };

const {reactive,ref} = await importShared('vue');


/**
 * 插件设置组件（Vue 联邦 Config 契约）
 * 收到 initialConfig 与 api，修改后持久化并 emit save
 */

const _sfc_main = {
  __name: 'Config',
  props: {
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, required: true },
  pluginId: { type: String, default: 'MyLibrary' },
},
  emits: ['save', 'close', 'switch'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;

const saving = ref(false);
const form = reactive({
  enabled: Boolean(props.initialConfig?.enabled),
  library_path: props.initialConfig?.library_path || '',
  poster_size: props.initialConfig?.poster_size || 'medium',
  douban_auto: props.initialConfig?.douban_auto !== false,
});

async function onSave() {
  saving.value = true;
  try {
    const cfg = {
      enabled: form.enabled,
      library_path: form.library_path,
      poster_size: form.poster_size,
      douban_auto: form.douban_auto,
    };
    await props.api.put(`plugin/${props.pluginId}`, cfg);
    emit('save', cfg);
    emit('switch', cfg.enabled);
  } finally {
    saving.value = false;
  }
}

return (_ctx, _cache) => {
  const _component_VSwitch = _resolveComponent("VSwitch");
  const _component_VCol = _resolveComponent("VCol");
  const _component_VTextField = _resolveComponent("VTextField");
  const _component_VSelect = _resolveComponent("VSelect");
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VRow = _resolveComponent("VRow");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_VRow, null, {
      default: _withCtx(() => [
        _createVNode(_component_VCol, { cols: "12" }, {
          default: _withCtx(() => [
            _createVNode(_component_VSwitch, {
              modelValue: form.enabled,
              "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((form.enabled) = $event)),
              label: "启用插件",
              color: "primary",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_VCol, { cols: "12" }, {
          default: _withCtx(() => [
            _createVNode(_component_VTextField, {
              modelValue: form.library_path,
              "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.library_path) = $event)),
              label: "媒体库目录",
              placeholder: "例如 /media/Videos",
              variant: "outlined",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_VCol, { cols: "12" }, {
          default: _withCtx(() => [
            _createVNode(_component_VSelect, {
              modelValue: form.poster_size,
              "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((form.poster_size) = $event)),
              label: "海报密度",
              items: [
            { title: '小', value: 'small' },
            { title: '中', value: 'medium' },
            { title: '大', value: 'original' },
          ],
              variant: "outlined",
              "hide-details": ""
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_VCol, { cols: "12" }, {
          default: _withCtx(() => [
            _createVNode(_component_VSwitch, {
              modelValue: form.douban_auto,
              "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((form.douban_auto) = $event)),
              label: "自动补齐豆瓣 ID",
              color: "primary",
              "hide-details": "",
              messages: "发现新片入库但没有豆瓣 ID 时，后台自动查询补上（每部间隔 1.2 秒，触发豆瓣限流会自动暂停）。关闭后只能手动跑 tools/fetch_douban_ids.py。"
            }, null, 8, ["modelValue"])
          ]),
          _: 1
        }),
        _createVNode(_component_VCol, {
          cols: "12",
          class: "d-flex justify-end"
        }, {
          default: _withCtx(() => [
            _createVNode(_component_VBtn, {
              color: "primary",
              loading: saving.value,
              onClick: onSave
            }, {
              default: _withCtx(() => [...(_cache[4] || (_cache[4] = [
                _createTextVNode("保存", -1)
              ]))]),
              _: 1
            }, 8, ["loading"])
          ]),
          _: 1
        })
      ]),
      _: 1
    })
  ]))
}
}

};

export { _sfc_main as default };
