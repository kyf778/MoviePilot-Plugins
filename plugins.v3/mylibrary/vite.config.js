import federation from '@originjs/vite-plugin-federation'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: 'MyLibrary',
      filename: 'remoteEntry.js',
      exposes: {
        './Page': './src/Page.vue',
        './AppPage': './src/AppPage.vue',
        './Config': './src/Config.vue',
      },
      shared: {
        vue: {
          requiredVersion: false,
          generate: false,
          singleton: true,
        },
        vuetify: {
          requiredVersion: false,
          generate: false,
          singleton: true,
        },
        'vuetify/styles': {
          requiredVersion: false,
          generate: false,
          singleton: true,
        },
      },
      format: 'esm',
    }),
  ],
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: true,
  },
  css: {
    postcss: {
      plugins: [
        {
          postcssPlugin: 'internal:charset-removal',
          AtRule: {
            charset: atRule => {
              if (atRule.name === 'charset') atRule.remove()
            },
          },
        },
        {
          // 联邦组件与主程序共用同一个 document，远程 CSS 会被追加到主页面 <head>。
          // Vuetify / MDI 的全局基础样式必须由主程序提供，插件重复打包会污染宿主界面，
          // 且离开插件页面后仍继续生效。因此按官方要求直接丢弃来自这两个包的 CSS。
          postcssPlugin: 'vuetify-filter',
          Root(root) {
            const sourcePath = (root.source?.input?.file || '').replaceAll('\\', '/')
            if (
              sourcePath.includes('/node_modules/vuetify/') ||
              sourcePath.includes('/node_modules/@mdi/')
            ) {
              root.nodes = []
              return
            }
            root.walkRules(rule => {
              if (rule.selector && (rule.selector.includes('.v-') || rule.selector.includes('.mdi-'))) {
                rule.remove()
              }
            })
          },
        },
      ],
    },
  },
})
