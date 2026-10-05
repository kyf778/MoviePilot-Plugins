import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import AppPage from './__federation_expose_AppPage-GI2z9Q3u.js';

const {openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');

/**
 * 插件详情页组件：复用 AppPage 海报墙
 */

const _sfc_main = {
  __name: 'Page',
  props: {
  api: { type: Object, required: true },
  pluginId: { type: String, required: true },
},
  setup(__props) {



return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(AppPage, {
    api: __props.api,
    "plugin-id": __props.pluginId,
    "nav-key": "main"
  }, null, 8, ["api", "plugin-id"]))
}
}

};

export { _sfc_main as default };
