import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

const {createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,resolveComponent:_resolveComponent,createVNode:_createVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,normalizeClass:_normalizeClass,mergeProps:_mergeProps} = await importShared('vue');


const _hoisted_1 = { class: "my-library-page pa-4" };
const _hoisted_2 = { class: "lib-header mb-4" };
const _hoisted_3 = { class: "lib-header-text" };
const _hoisted_4 = { class: "text-caption text-medium-emphasis" };
const _hoisted_5 = ["title"];
const _hoisted_6 = { class: "lib-toolbar mb-4" };
const _hoisted_7 = { class: "text-caption text-medium-emphasis mx-2" };
const _hoisted_8 = {
  key: 0,
  class: "lib-grid"
};
const _hoisted_9 = {
  key: 3,
  class: "lib-grid"
};
const _hoisted_10 = {
  key: 0,
  class: "lib-poster-placeholder"
};
const _hoisted_11 = {
  key: 2,
  class: "lib-hover-layer"
};
const _hoisted_12 = { class: "lib-hover-year" };
const _hoisted_13 = { class: "lib-hover-title" };
const _hoisted_14 = { class: "lib-hover-overview" };
const _hoisted_15 = { class: "lib-hover-meta" };
const _hoisted_16 = ["onClick"];
const _hoisted_17 = { class: "lib-row-poster" };
const _hoisted_18 = ["src"];
const _hoisted_19 = { class: "lib-row-main" };
const _hoisted_20 = { class: "lib-row-title" };
const _hoisted_21 = { class: "text-medium-emphasis" };
const _hoisted_22 = { class: "lib-row-sub text-caption text-medium-emphasis" };
const _hoisted_23 = { class: "text-caption text-medium-emphasis lib-row-meta" };
const _hoisted_24 = { class: "lib-detail-back" };
const _hoisted_25 = { class: "lib-detail-header" };
const _hoisted_26 = { class: "lib-detail-poster" };
const _hoisted_27 = ["src"];
const _hoisted_28 = {
  key: 1,
  class: "lib-poster-placeholder d-flex align-center justify-center"
};
const _hoisted_29 = { class: "lib-detail-title" };
const _hoisted_30 = { class: "lib-detail-name" };
const _hoisted_31 = {
  key: 0,
  class: "lib-detail-year"
};
const _hoisted_32 = { class: "lib-detail-attrs" };
const _hoisted_33 = { key: 0 };
const _hoisted_34 = {
  key: 1,
  class: "mx-1"
};
const _hoisted_35 = { key: 2 };
const _hoisted_36 = { class: "d-flex flex-wrap ga-2 mt-3" };
const _hoisted_37 = { class: "lib-detail-left" };
const _hoisted_38 = { class: "lib-detail-overview" };
const _hoisted_39 = {
  key: 0,
  class: "lib-crew"
};
const _hoisted_40 = { class: "lib-source-links mt-4" };
const _hoisted_41 = ["href"];
const _hoisted_42 = ["href"];
const _hoisted_43 = ["href"];
const _hoisted_44 = { class: "lib-files" };

const {computed,onMounted,ref} = await importShared('vue');


/**
 * 我的媒体库 —— 海报墙（照搬 MoviePilot 官方 MediaCard 的交互与视觉）
 *   卡片：纯海报 2:3，悬停浮出渐变详情层（年份/片名/简介），左上映类型角标，右上评分角标
 *   详情：完整信息弹窗（演职员、清晰度、文件清单、体积等）
 */

const _sfc_main = {
  __name: 'AppPage',
  props: {
  api: { type: Object, required: true },
  pluginId: { type: String, required: true },
  navKey: { type: String, default: 'main' },
},
  setup(__props) {

const props = __props;

const loading = ref(true);
const errorMsg = ref('');
const summary = ref({ total: 0, movies: 0, tvs: 0, total_size: '0 B' });
const libraryPath = ref('');
const items = ref([]);

const viewType = ref(localStorage.getItem('mylibrary.view') || 'card');
function toggleView() {
  viewType.value = viewType.value === 'card' ? 'row' : 'card';
  localStorage.setItem('mylibrary.view', viewType.value);
}

const keyword = ref('');
const typeFilter = ref('全部');
const resolutionFilter = ref('全部');

const resolutions = computed(() => {
  const set = new Set(items.value.map(i => i.resolution).filter(Boolean));
  return ['全部', ...Array.from(set).sort()]
});

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase();
  return items.value.filter(it => {
    if (typeFilter.value !== '全部' && it.type !== typeFilter.value) return false
    if (resolutionFilter.value !== '全部' && (it.resolution || '未知') !== resolutionFilter.value) return false
    if (!kw) return true
    return (
      String(it.title || '').toLowerCase().includes(kw) ||
      String(it.year || '').includes(kw) ||
      String(it.director || '').toLowerCase().includes(kw) ||
      String(it.dir_name || '').toLowerCase().includes(kw)
    )
  })
});

// 排序
const sortBy = ref('title');
const sorted = computed(() => {
  const arr = filtered.value.slice();
  const byYearDesc = (a, b) => (parseInt(b.year) || 0) - (parseInt(a.year) || 0);
  const bySizeDesc = (a, b) => (b.size_bytes || 0) - (a.size_bytes || 0);
  const byRatingDesc = (a, b) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0);
  if (sortBy.value === 'year') arr.sort(byYearDesc);
  else if (sortBy.value === 'size') arr.sort(bySizeDesc);
  else if (sortBy.value === 'rating') arr.sort(byRatingDesc);
  else arr.sort((a, b) => String(a.title).localeCompare(String(b.title), 'zh'));
  return arr
});

const detail = ref(null);
ref('info');
ref(false);

async function load() {
  loading.value = true;
  errorMsg.value = '';
  try {
    const res = await props.api.get(`plugin/${props.pluginId}/library`);
    if (res && res.success && res.data) {
      items.value = res.data.items || [];
      summary.value = res.data.summary || summary.value;
      libraryPath.value = res.data.library_path || '';
    } else {
      errorMsg.value = (res && res.message) || '接口返回异常';
    }
  } catch (e) {
    errorMsg.value = String(e?.message || e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

/** 角标配色：对齐官方 MediaCard.getChipColor */
function typeChipClass(type) {
  if (type === '电影') return 'bg-blue-600'
  if (type === '电视剧') return 'bg-indigo-500'
  if (type === '音乐') return 'bg-pink-600'
  return 'bg-purple-600'
}

function ratingText(rating) {
  const r = parseFloat(rating);
  return Number.isNaN(r) || !r ? '' : r.toFixed(1)
}

/** 评分配色：按分数高低 */
function ratingColor(rating) {
  const r = parseFloat(rating) || 0;
  if (r >= 8) return 'bg-green-600'
  if (r >= 6.5) return 'bg-amber-600'
  return 'bg-orange-700'
}

/** 分钟 → 1h 47m */
function durationText(min) {
  const m = parseInt(min);
  if (!m || Number.isNaN(m)) return ''
  const h = Math.floor(m / 60);
  const r = m % 60;
  return h ? `${h} 小时 ${r} 分` : `${r} 分钟`
}

/**
 * 横版背景图：对齐官方——优先 landscape.jpg（正常横构图）。
 * 注意：fanart/backdrop 在很多片子里是"枪管/隧道"主观视角构图（如 007），
 * 直接当背景会出现中间的圆形亮斑，观感很差，故不用。
 * landscape 缺失时回退 thumb（两者同图），再回退竖版海报。
 */
function backdropUrl(item) {
  if (!item?.dir_name) return ''
  const base = `/api/v1/plugin/${props.pluginId}/poster?path=${encodeURIComponent(item.dir_name)}`;
  return item.has_landscape ? `${base}/landscape.jpg` : item.poster_url
}

/**
 * 豆瓣链接：nfo 里没有 <doubanid>（实测 0/50），豆瓣网页搜索又有反爬限流，
 * 因此由 scripts/fetch_douban_ids.py 预先抓取 49 部豆瓣 id 落盘为 .douban_ids.json，
 * 后端读缓存后随条目返回 douban_id。这里只负责拼链接；无 id 时回退到搜索页。
 */
function doubanUrl(item) {
  if (item?.douban_id) {
    return `https://movie.douban.com/subject/${item.douban_id}/`
  }
  const kw = [item?.title, item?.year].filter(Boolean).join(' ');
  return `https://search.douban.com/movie/subject_search?search_text=${encodeURIComponent(kw)}`
}

return (_ctx, _cache) => {
  const _component_VIcon = _resolveComponent("VIcon");
  const _component_VTextField = _resolveComponent("VTextField");
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VBtnToggle = _resolveComponent("VBtnToggle");
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VSelect = _resolveComponent("VSelect");
  const _component_VTooltip = _resolveComponent("VTooltip");
  const _component_VSkeletonLoader = _resolveComponent("VSkeletonLoader");
  const _component_VCard = _resolveComponent("VCard");
  const _component_VAlert = _resolveComponent("VAlert");
  const _component_VImg = _resolveComponent("VImg");
  const _component_VChip = _resolveComponent("VChip");
  const _component_VHover = _resolveComponent("VHover");
  const _component_VExpansionPanelText = _resolveComponent("VExpansionPanelText");
  const _component_VExpansionPanel = _resolveComponent("VExpansionPanel");
  const _component_VExpansionPanels = _resolveComponent("VExpansionPanels");
  const _component_VCardText = _resolveComponent("VCardText");
  const _component_VDialog = _resolveComponent("VDialog");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _createElementVNode("div", _hoisted_3, [
        _cache[6] || (_cache[6] = _createElementVNode("div", { class: "text-h6 font-weight-bold" }, "我的媒体库", -1)),
        _createElementVNode("div", _hoisted_4, " 共 " + _toDisplayString(summary.value.total) + " 部 · 电影 " + _toDisplayString(summary.value.movies) + " · 电视剧 " + _toDisplayString(summary.value.tvs) + " · 占用 " + _toDisplayString(summary.value.total_size), 1)
      ]),
      _createElementVNode("div", {
        class: "lib-header-path text-caption text-medium-emphasis",
        title: libraryPath.value
      }, [
        _createVNode(_component_VIcon, {
          icon: "mdi-folder-outline",
          size: "14",
          class: "mr-1"
        }),
        _createTextVNode(_toDisplayString(libraryPath.value), 1)
      ], 8, _hoisted_5)
    ]),
    _createElementVNode("div", _hoisted_6, [
      _createVNode(_component_VTextField, {
        modelValue: keyword.value,
        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((keyword).value = $event)),
        placeholder: "搜索片名 / 年份 / 导演…",
        "prepend-inner-icon": "mdi-magnify",
        density: "compact",
        "hide-details": "",
        variant: "outlined",
        class: "lib-search",
        clearable: ""
      }, null, 8, ["modelValue"]),
      _createVNode(_component_VBtnToggle, {
        modelValue: typeFilter.value,
        "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((typeFilter).value = $event)),
        divided: "",
        density: "compact",
        variant: "outlined",
        mandatory: ""
      }, {
        default: _withCtx(() => [
          _createVNode(_component_VBtn, { value: "全部" }, {
            default: _withCtx(() => [...(_cache[7] || (_cache[7] = [
              _createTextVNode("全部", -1)
            ]))]),
            _: 1
          }),
          _createVNode(_component_VBtn, { value: "电影" }, {
            default: _withCtx(() => [...(_cache[8] || (_cache[8] = [
              _createTextVNode("电影", -1)
            ]))]),
            _: 1
          }),
          _createVNode(_component_VBtn, { value: "电视剧" }, {
            default: _withCtx(() => [...(_cache[9] || (_cache[9] = [
              _createTextVNode("电视剧", -1)
            ]))]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["modelValue"]),
      (resolutions.value.length > 2)
        ? (_openBlock(), _createBlock(_component_VBtnToggle, {
            key: 0,
            modelValue: resolutionFilter.value,
            "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((resolutionFilter).value = $event)),
            divided: "",
            density: "compact",
            variant: "outlined",
            mandatory: ""
          }, {
            default: _withCtx(() => [
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(resolutions.value, (r) => {
                return (_openBlock(), _createBlock(_component_VBtn, {
                  key: r,
                  value: r
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(r), 1)
                  ]),
                  _: 2
                }, 1032, ["value"]))
              }), 128))
            ]),
            _: 1
          }, 8, ["modelValue"]))
        : _createCommentVNode("", true),
      _createVNode(_component_VSpacer),
      _createVNode(_component_VSelect, {
        modelValue: sortBy.value,
        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((sortBy).value = $event)),
        items: [
          { title: '按片名', value: 'title' },
          { title: '按年份 ↓', value: 'year' },
          { title: '按评分 ↓', value: 'rating' },
          { title: '按体积 ↓', value: 'size' },
        ],
        density: "compact",
        "hide-details": "",
        variant: "outlined",
        style: {"max-width":"150px"}
      }, null, 8, ["modelValue"]),
      _createElementVNode("span", _hoisted_7, _toDisplayString(sorted.value.length) + " / " + _toDisplayString(summary.value.total), 1),
      _createVNode(_component_VBtn, {
        density: "compact",
        variant: "tonal",
        size: "small",
        icon: "",
        onClick: toggleView
      }, {
        default: _withCtx(() => [
          _createVNode(_component_VIcon, {
            icon: viewType.value === 'card' ? 'mdi-view-list-outline' : 'mdi-view-grid-outline'
          }, null, 8, ["icon"]),
          _createVNode(_component_VTooltip, {
            activator: "parent",
            location: "bottom"
          }, {
            default: _withCtx(() => [
              _createTextVNode(_toDisplayString(viewType.value === 'card' ? '切换列表视图' : '切换海报墙'), 1)
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    (loading.value)
      ? (_openBlock(), _createElementBlock("div", _hoisted_8, [
          (_openBlock(), _createElementBlock(_Fragment, null, _renderList(18, (i) => {
            return _createVNode(_component_VCard, {
              key: i,
              elevation: "0",
              class: "lib-skeleton"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VSkeletonLoader, { type: "image, article" })
              ]),
              _: 1
            })
          }), 64))
        ]))
      : (errorMsg.value)
        ? (_openBlock(), _createBlock(_component_VAlert, {
            key: 1,
            type: "error",
            variant: "tonal"
          }, {
            append: _withCtx(() => [
              _createVNode(_component_VBtn, {
                size: "small",
                variant: "tonal",
                onClick: load
              }, {
                default: _withCtx(() => [...(_cache[10] || (_cache[10] = [
                  _createTextVNode("重试", -1)
                ]))]),
                _: 1
              })
            ]),
            default: _withCtx(() => [
              _createTextVNode(" 加载失败：" + _toDisplayString(errorMsg.value) + " ", 1)
            ]),
            _: 1
          }))
        : (!sorted.value.length)
          ? (_openBlock(), _createBlock(_component_VAlert, {
              key: 2,
              type: "info",
              variant: "tonal"
            }, {
              default: _withCtx(() => [
                _createTextVNode(_toDisplayString(items.value.length ? '没有匹配的影片' : '未扫描到媒体，请在插件设置中填写媒体库目录'), 1)
              ]),
              _: 1
            }))
          : (viewType.value === 'card')
            ? (_openBlock(), _createElementBlock("div", _hoisted_9, [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sorted.value, (it) => {
                  return (_openBlock(), _createBlock(_component_VHover, {
                    key: it.dir_name
                  }, {
                    default: _withCtx(({ isHovering, props: hoverProps }) => [
                      _createElementVNode("div", _mergeProps({ ref_for: true }, hoverProps, { class: "lib-hover-area" }), [
                        _createVNode(_component_VCard, {
                          class: _normalizeClass(["lib-poster-card", { 'lib-poster-card--hover': isHovering }]),
                          onClick: $event => (detail.value = it)
                        }, {
                          default: _withCtx(() => [
                            (!it.has_poster)
                              ? (_openBlock(), _createElementBlock("div", _hoisted_10, [
                                  _createVNode(_component_VIcon, {
                                    icon: "mdi-movie-open-outline",
                                    size: "56",
                                    color: "medium-emphasis"
                                  })
                                ]))
                              : (_openBlock(), _createBlock(_component_VImg, {
                                  key: 1,
                                  src: it.poster_url,
                                  "aspect-ratio": 2 / 3,
                                  cover: "",
                                  class: "lib-poster-img"
                                }, {
                                  placeholder: _withCtx(() => [
                                    _createVNode(_component_VSkeletonLoader, { class: "lib-poster-img" })
                                  ]),
                                  _: 1
                                }, 8, ["src"])),
                            isHovering
                              ? (_openBlock(), _createElementBlock("div", _hoisted_11, [
                                  _createElementVNode("span", _hoisted_12, _toDisplayString(it.year), 1),
                                  _createElementVNode("h1", _hoisted_13, _toDisplayString(it.title), 1),
                                  _createElementVNode("p", _hoisted_14, _toDisplayString(it.overview || '暂无简介'), 1),
                                  _createElementVNode("div", _hoisted_15, [
                                    (it.resolution)
                                      ? (_openBlock(), _createBlock(_component_VChip, {
                                          key: 0,
                                          size: "x-small",
                                          class: "bg-purple-600",
                                          variant: "elevated"
                                        }, {
                                          default: _withCtx(() => [
                                            _createTextVNode(_toDisplayString(it.resolution), 1)
                                          ]),
                                          _: 2
                                        }, 1024))
                                      : _createCommentVNode("", true),
                                    _createVNode(_component_VChip, {
                                      size: "x-small",
                                      class: "bg-teal-600",
                                      variant: "elevated"
                                    }, {
                                      default: _withCtx(() => [
                                        _createTextVNode(_toDisplayString(it.size_display), 1)
                                      ]),
                                      _: 2
                                    }, 1024),
                                    _createVNode(_component_VSpacer),
                                    _createVNode(_component_VIcon, {
                                      icon: "mdi-information-outline",
                                      size: "16"
                                    })
                                  ])
                                ]))
                              : _createCommentVNode("", true),
                            _createVNode(_component_VChip, {
                              size: "small",
                              variant: "elevated",
                              class: _normalizeClass([typeChipClass(it.type), "lib-badge-tl"])
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode(_toDisplayString(it.type), 1)
                              ]),
                              _: 2
                            }, 1032, ["class"]),
                            (ratingText(it.rating))
                              ? (_openBlock(), _createBlock(_component_VChip, {
                                  key: 3,
                                  size: "small",
                                  variant: "elevated",
                                  class: _normalizeClass([ratingColor(it.rating), "lib-badge-tr"])
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode(_toDisplayString(ratingText(it.rating)), 1)
                                  ]),
                                  _: 2
                                }, 1032, ["class"]))
                              : _createCommentVNode("", true),
                            (it.type === '电视剧' && it.season_count)
                              ? (_openBlock(), _createBlock(_component_VChip, {
                                  key: 4,
                                  size: "x-small",
                                  variant: "elevated",
                                  color: "primary",
                                  class: "lib-badge-br"
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode(_toDisplayString(it.season_count) + " 季 ", 1)
                                  ]),
                                  _: 2
                                }, 1024))
                              : _createCommentVNode("", true)
                          ]),
                          _: 2
                        }, 1032, ["class", "onClick"])
                      ], 16)
                    ]),
                    _: 2
                  }, 1024))
                }), 128))
              ]))
            : (_openBlock(), _createBlock(_component_VCard, {
                key: 4,
                elevation: "0",
                class: "lib-rows"
              }, {
                default: _withCtx(() => [
                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sorted.value, (it) => {
                    return (_openBlock(), _createElementBlock("div", {
                      key: it.dir_name,
                      class: "lib-row",
                      onClick: $event => (detail.value = it)
                    }, [
                      _createElementVNode("div", _hoisted_17, [
                        (it.poster_url)
                          ? (_openBlock(), _createElementBlock("img", {
                              key: 0,
                              src: it.poster_url,
                              loading: "lazy",
                              alt: ""
                            }, null, 8, _hoisted_18))
                          : (_openBlock(), _createBlock(_component_VIcon, {
                              key: 1,
                              icon: "mdi-movie-open-outline",
                              size: "20",
                              opacity: "0.4"
                            }))
                      ]),
                      _createElementVNode("div", _hoisted_19, [
                        _createElementVNode("div", _hoisted_20, [
                          _createTextVNode(_toDisplayString(it.title), 1),
                          _createElementVNode("span", _hoisted_21, "（" + _toDisplayString(it.year) + "）", 1)
                        ]),
                        _createElementVNode("div", _hoisted_22, [
                          _createVNode(_component_VChip, {
                            size: "x-small",
                            variant: "tonal",
                            class: "mr-1"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(it.type), 1)
                            ]),
                            _: 2
                          }, 1024),
                          (it.resolution)
                            ? (_openBlock(), _createBlock(_component_VChip, {
                                key: 0,
                                size: "x-small",
                                variant: "tonal",
                                class: "mr-1"
                              }, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString(it.resolution), 1)
                                ]),
                                _: 2
                              }, 1024))
                            : _createCommentVNode("", true),
                          _createTextVNode(" " + _toDisplayString(it.genre || '未知类型'), 1)
                        ])
                      ]),
                      _createElementVNode("span", _hoisted_23, _toDisplayString(it.size_display), 1),
                      (ratingText(it.rating))
                        ? (_openBlock(), _createBlock(_component_VChip, {
                            key: 0,
                            size: "x-small",
                            variant: "tonal",
                            color: "amber-darken-3"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(ratingText(it.rating)), 1)
                            ]),
                            _: 2
                          }, 1024))
                        : _createCommentVNode("", true),
                      _createVNode(_component_VIcon, {
                        icon: "mdi-chevron-right",
                        size: "18",
                        color: "medium-emphasis"
                      })
                    ], 8, _hoisted_16))
                  }), 128))
                ]),
                _: 1
              })),
    _createVNode(_component_VDialog, {
      modelValue: detail.value,
      "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((detail).value = $event)),
      "max-width": "1000",
      scrollable: ""
    }, {
      default: _withCtx(() => [
        (detail.value)
          ? (_openBlock(), _createBlock(_component_VCard, {
              key: 0,
              class: "lib-detail"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VBtn, {
                  icon: "mdi-close",
                  size: "small",
                  variant: "tonal",
                  class: "lib-detail-close",
                  onClick: _cache[4] || (_cache[4] = $event => (detail.value = null))
                }),
                _createElementVNode("div", _hoisted_24, [
                  _createVNode(_component_VImg, {
                    src: backdropUrl(detail.value),
                    cover: "",
                    position: "top",
                    class: "lib-detail-back-img"
                  }, {
                    placeholder: _withCtx(() => [...(_cache[11] || (_cache[11] = [
                      _createElementVNode("div", { class: "lib-detail-back-skeleton" }, null, -1)
                    ]))]),
                    _: 1
                  }, 8, ["src"]),
                  _cache[12] || (_cache[12] = _createElementVNode("div", { class: "lib-detail-back-overlay" }, null, -1))
                ]),
                _createElementVNode("div", _hoisted_25, [
                  _createElementVNode("div", _hoisted_26, [
                    (detail.value.poster_url)
                      ? (_openBlock(), _createElementBlock("img", {
                          key: 0,
                          src: detail.value.poster_url,
                          alt: ""
                        }, null, 8, _hoisted_27))
                      : (_openBlock(), _createElementBlock("div", _hoisted_28, [
                          _createVNode(_component_VIcon, {
                            icon: "mdi-movie-open-outline",
                            size: "44",
                            color: "medium-emphasis"
                          })
                        ]))
                  ]),
                  _createElementVNode("div", _hoisted_29, [
                    _createElementVNode("h1", _hoisted_30, [
                      _createTextVNode(_toDisplayString(detail.value.title) + " ", 1),
                      (detail.value.year)
                        ? (_openBlock(), _createElementBlock("span", _hoisted_31, "（" + _toDisplayString(detail.value.year) + "）", 1))
                        : _createCommentVNode("", true)
                    ]),
                    _createElementVNode("span", _hoisted_32, [
                      (durationText(detail.value.duration))
                        ? (_openBlock(), _createElementBlock("span", _hoisted_33, _toDisplayString(durationText(detail.value.duration)), 1))
                        : _createCommentVNode("", true),
                      (durationText(detail.value.duration) && detail.value.genre)
                        ? (_openBlock(), _createElementBlock("span", _hoisted_34, "|"))
                        : _createCommentVNode("", true),
                      (detail.value.genre)
                        ? (_openBlock(), _createElementBlock("span", _hoisted_35, _toDisplayString(detail.value.genre.split(/[\/,、]/).slice(0, 3).join('、')), 1))
                        : _createCommentVNode("", true)
                    ]),
                    _createElementVNode("div", _hoisted_36, [
                      _createVNode(_component_VChip, {
                        size: "small",
                        variant: "elevated",
                        class: _normalizeClass(typeChipClass(detail.value.type))
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(detail.value.type), 1)
                        ]),
                        _: 1
                      }, 8, ["class"]),
                      (detail.value.resolution)
                        ? (_openBlock(), _createBlock(_component_VChip, {
                            key: 0,
                            size: "small",
                            variant: "tonal",
                            color: "deep-purple"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(detail.value.resolution), 1)
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode("", true),
                      (detail.value.mpaa)
                        ? (_openBlock(), _createBlock(_component_VChip, {
                            key: 1,
                            size: "small",
                            variant: "tonal"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(detail.value.mpaa), 1)
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode("", true),
                      _createVNode(_component_VChip, {
                        size: "small",
                        variant: "tonal",
                        color: "teal"
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(detail.value.size_display), 1)
                        ]),
                        _: 1
                      }),
                      (detail.value.video_count > 1)
                        ? (_openBlock(), _createBlock(_component_VChip, {
                            key: 2,
                            size: "small",
                            variant: "tonal"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(detail.value.video_count) + " 个文件 ", 1)
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode("", true)
                    ])
                  ])
                ]),
                _createVNode(_component_VCardText, { class: "lib-detail-body" }, {
                  default: _withCtx(() => [
                    _createElementVNode("div", _hoisted_37, [
                      _createElementVNode("p", _hoisted_38, _toDisplayString(detail.value.overview || '暂无简介'), 1),
                      (detail.value.cast && detail.value.cast.length)
                        ? (_openBlock(), _createElementBlock("ul", _hoisted_39, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.value.cast.slice(0, 12), (c, i) => {
                              return (_openBlock(), _createElementBlock("li", { key: i }, [
                                _createElementVNode("span", null, _toDisplayString(c.tag_text), 1),
                                _createElementVNode("b", null, _toDisplayString(c.name), 1)
                              ]))
                            }), 128))
                          ]))
                        : _createCommentVNode("", true),
                      _createElementVNode("div", _hoisted_40, [
                        (detail.value.tmdb_id)
                          ? (_openBlock(), _createElementBlock("a", {
                              key: 0,
                              href: `https://www.themoviedb.org/movie/${detail.value.tmdb_id}`,
                              target: "_blank",
                              rel: "noopener",
                              class: "lib-source-chip"
                            }, [
                              _createVNode(_component_VIcon, {
                                icon: "mdi-link",
                                size: "14",
                                class: "mr-1"
                              }),
                              _cache[13] || (_cache[13] = _createTextVNode("TheMovieDb ", -1))
                            ], 8, _hoisted_41))
                          : _createCommentVNode("", true),
                        (detail.value.imdb_id)
                          ? (_openBlock(), _createElementBlock("a", {
                              key: 1,
                              href: `https://www.imdb.com/title/${detail.value.imdb_id}`,
                              target: "_blank",
                              rel: "noopener",
                              class: "lib-source-chip"
                            }, [
                              _createVNode(_component_VIcon, {
                                icon: "mdi-link",
                                size: "14",
                                class: "mr-1"
                              }),
                              _cache[14] || (_cache[14] = _createTextVNode("IMDb ", -1))
                            ], 8, _hoisted_42))
                          : _createCommentVNode("", true),
                        _createElementVNode("a", {
                          href: doubanUrl(detail.value),
                          target: "_blank",
                          rel: "noopener",
                          class: "lib-source-chip"
                        }, [
                          _createVNode(_component_VIcon, {
                            icon: "mdi-link",
                            size: "14",
                            class: "mr-1"
                          }),
                          _cache[15] || (_cache[15] = _createTextVNode("豆瓣 ", -1))
                        ], 8, _hoisted_43)
                      ]),
                      (detail.value.video_files && detail.value.video_files.length)
                        ? (_openBlock(), _createBlock(_component_VExpansionPanels, {
                            key: 1,
                            class: "mt-4"
                          }, {
                            default: _withCtx(() => [
                              _createVNode(_component_VExpansionPanel, {
                                title: `文件清单（${detail.value.video_files.length}）`
                              }, {
                                default: _withCtx(() => [
                                  _createVNode(_component_VExpansionPanelText, null, {
                                    default: _withCtx(() => [
                                      _createElementVNode("div", _hoisted_44, [
                                        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.value.video_files, (f, i) => {
                                          return (_openBlock(), _createElementBlock("div", {
                                            key: i,
                                            class: "lib-file text-caption"
                                          }, [
                                            _createVNode(_component_VIcon, {
                                              icon: "mdi-film",
                                              size: "14",
                                              class: "mr-2"
                                            }),
                                            _createTextVNode(_toDisplayString(f.name), 1)
                                          ]))
                                        }), 128))
                                      ])
                                    ]),
                                    _: 1
                                  })
                                ]),
                                _: 1
                              }, 8, ["title"])
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode("", true)
                    ])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true)
      ]),
      _: 1
    }, 8, ["modelValue"])
  ]))
}
}

};
const AppPage = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-2b2f8a16"]]);

export { AppPage as default };
