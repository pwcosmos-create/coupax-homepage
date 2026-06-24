const API_URL = "/api/v1/shorts/generate-pipeline";
const CHECKOUT_URL = "/api/v1/shorts/checkout";
const SUB_URL = "/api/v1/shorts/subscription";
const cfg = window.SHORTS_CONFIG || {};
const SUPPORTED_LANGS = ["ko", "en", "ja", "zh", "es"];

const I18N = {
  en: {
    nav_features: "Features",
    nav_pricing: "Pricing",
    nav_studio: "Studio",
    cta_subscribe: "Subscribe",
    hero_eyebrow: "Subscribe + your Gemini API key",
    hero_title: "AI short-form promos for local businesses",
    hero_lead:
      "Enter your shop details. We run Gemini scripts, Imagen frames, Veo clips, and Lyria BGM — delivered as ready-to-edit 9:16 assets.",
    hero_cta_primary: "View plans",
    hero_cta_secondary: "Open studio",
    chip_script: "Script",
    chip_video: "Video",
    features_title: "Built for shop owners worldwide",
    f1_title: "Subscribe & create",
    f1_body: "Monthly subscription for quota. Run the pipeline with your own Google AI API key.",
    f2_title: "Full AI pipeline",
    f2_body: "Scenario, visuals, motion, and music in one workflow tuned for vertical promos.",
    f3_title: "Scene-by-scene output",
    f3_body: "Captions, narration, and per-scene assets you can drop into CapCut or Reels.",
    pricing_title: "Simple monthly plans",
    pricing_lead: "All plans include the full pipeline. Quota resets every billing period.",
    plan_popular: "Popular",
    plan_per_month: "/mo",
    plan_shorts: "shorts / month",
    plan_shorts_daily: "shorts / day",
    plan_unlimited: "Unlimited",
    plan_free: "Free",
    btn_start_free: "Start free",
    plan_subscribe: "Subscribe",
    payments_paid_soon: "Pro and Business checkout is coming soon. Starter is free to use.",
    payments_soon: "Payments are being configured. Check back soon.",
    studio_title: "Studio",
    studio_lead: "Subscribers generate shorts with their own Google AI API key.",
    sub_required: "Subscription required",
    quota_remaining: "{n} / {q} left",
    quota_remaining_daily: "{n} / {q} left today",
    quota_unlimited: "Unlimited",
    form_title: "Generate a short",
    label_api_key: "Google AI API key (yours)",
    label_shop: "Shop name",
    label_concept: "Concept / signature menu",
    label_concept_badge: "Most important",
    concept_hint: "Write 3–5 sentences, not just one line.",
    concept_example_label: "Example",
    btn_load_example: "Load example",
    shop_example: "Matdon Katsu",
    concept_example:
      "Handmade tonkatsu shop using Jeju black pork.\nSignature: crispy-outside, juicy-inside cheese tonkatsu (long cheese pull).\nLunch set $8.99, group bookings welcome.\nWarm wood interior, popular with families and couples.\nInstagram-style shorts targeting young customers.",
    label_style: "Style",
    label_duration: "Duration",
    btn_generate: "Run pipeline",
    results_title: "Results",
    results_empty: "No shorts yet. Fill the form and run the pipeline.",
    loading: "Running AI pipeline…",
    loading_steps: [
      "Writing Gemini script…",
      "Rendering Lyria BGM…",
      "Generating Imagen frames…",
      "Converting with Veo…",
      "Packaging assets…",
    ],
    err_subscribe: "Active subscription required. Please subscribe first.",
    checkout_err: "Checkout failed.",
    done: "Generation complete",
    scene_rendered: "Rendered",
    footer_note: "Powered by Google AI · Built for local business promos",
    privacy_note: "We do not store personal information or API keys on our servers. They may be saved on your device only.",
    api_key_privacy: "Not stored on our servers. May be remembered on this device (phone or PC) for your convenience.",
    api_key_guide_title: "How to get a Gemini API key",
    api_key_step1: "Open Google AI Studio (aistudio.google.com/apikey).",
    api_key_step2: "Sign in with your Google account.",
    api_key_step3: "Click “Create API key”.",
    api_key_step4: "Copy the key (AIza...) and paste it above.",
    api_key_billing_note: "API usage is billed to your Google account.",
    btn_show_key: "Show",
    btn_hide_key: "Hide",
    err_shop_name_required: "Enter your shop name first.",
    concept_preview_empty: "Enter a shop name to see a tailored example here.",
    concept_load_note: "Draft is based on your shop name. Edit freely before generating.",
    err_api_key_invalid: "Invalid Google AI API key format.",
    hero_captions: ["Cheese waterfall!", "Crispy outside, juicy inside", "Lunch special today?"],
  },
  ko: {
    nav_features: "기능",
    nav_pricing: "요금제",
    nav_studio: "스튜디오",
    cta_subscribe: "구독하기",
    hero_eyebrow: "구독 + 본인 Gemini API 키",
    hero_title: "소상공인을 위한 AI 숏폼 홍보",
    hero_lead:
      "매장 정보만 입력하세요. Gemini 시나리오, Imagen 이미지, Veo 영상, Lyria BGM을 9:16 자산으로 제공합니다.",
    hero_cta_primary: "요금제 보기",
    hero_cta_secondary: "스튜디오 열기",
    chip_script: "시나리오",
    chip_video: "영상",
    features_title: "전 세계 매장 사장님을 위해",
    f1_title: "구독하고 바로 생성",
    f1_body: "월 구독으로 쿼터를 사용하고, 본인 Google AI API 키로 파이프라인을 실행합니다.",
    f2_title: "풀 AI 파이프라인",
    f2_body: "세로 홍보에 맞춘 시나리오·비주얼·모션·음악 원스톱 워크플로.",
    f3_title: "장면별 결과물",
    f3_body: "자막·내레이션·장면 자산을 캡컷·릴스에 바로 넣을 수 있습니다.",
    pricing_title: "간단한 월 요금제",
    pricing_lead: "모든 플랜에 전체 파이프라인 포함. 결제 주기마다 쿼터가 초기화됩니다.",
    plan_popular: "인기",
    plan_per_month: "/월",
    plan_shorts: "숏폼 / 월",
    plan_shorts_daily: "숏폼 / 일",
    plan_unlimited: "무제한",
    plan_free: "무료",
    btn_start_free: "무료 시작",
    plan_subscribe: "구독하기",
    payments_paid_soon: "Pro·Business 결제는 준비 중입니다. 스타터는 무료로 이용할 수 있습니다.",
    payments_soon: "결제 설정 중입니다. 곧 이용 가능합니다.",
    studio_title: "스튜디오",
    studio_lead: "구독 회원은 본인 Google AI API 키로 숏폼을 생성합니다.",
    sub_required: "구독이 필요합니다",
    quota_remaining: "잔여 {n} / {q}",
    quota_remaining_daily: "오늘 잔여 {n} / {q}",
    quota_unlimited: "무제한",
    form_title: "숏폼 생성",
    label_api_key: "Google AI API 키 (본인 키)",
    label_shop: "매장명",
    label_concept: "컨셉 / 대표 메뉴",
    label_concept_badge: "가장 중요",
    concept_hint: "한 줄이 아니라 3~5문장으로 쓰는 게 좋습니다.",
    concept_example_label: "작성 예시",
    btn_load_example: "예시 불러오기",
    shop_example: "맛돈 카츠",
    concept_example:
      "제주 흑돼지로 만든 수제 돈까스 전문점.\n시그니처는 겉바속촉 치즈 돈까스(치즈가 길게 늘어남).\n점심 세트 9,900원, 단체 예약 가능.\n따뜻한 우드 인테리어, 가족·커플 방문 많음.\n인스타 감성 숏폼으로 젊은 층 타깃.",
    label_style: "영상 스타일",
    label_duration: "길이",
    btn_generate: "파이프라인 실행",
    results_title: "생성 결과",
    results_empty: "아직 생성된 숏폼이 없습니다. 폼을 작성하고 실행해 보세요.",
    loading: "AI 파이프라인 실행 중…",
    loading_steps: [
      "Gemini 시나리오 생성 중…",
      "Lyria BGM 렌더링 중…",
      "Imagen 이미지 생성 중…",
      "Veo 비디오 변환 중…",
      "최종 자산 패키징 중…",
    ],
    err_subscribe: "활성 구독이 필요합니다. 먼저 구독해 주세요.",
    checkout_err: "결제 시작에 실패했습니다.",
    done: "생성 완료",
    scene_rendered: "렌더 완료",
    footer_note: "Google AI 기반 · 소상공인 홍보용",
    privacy_note: "서버에는 개인정보·API 키를 저장하지 않습니다. 사용자 기기(휴대폰·PC)에만 저장될 수 있습니다.",
    api_key_privacy: "서버에는 저장하지 않으며, 편의를 위해 이 기기(휴대폰·PC)에만 기억할 수 있습니다.",
    api_key_guide_title: "Gemini API 키 발급 방법",
    api_key_step1: "Google AI Studio(aistudio.google.com/apikey)에 접속합니다.",
    api_key_step2: "Google 계정으로 로그인합니다.",
    api_key_step3: "「API 키 만들기」 또는 「Create API key」를 클릭합니다.",
    api_key_step4: "생성된 키(AIza...)를 복사해 위 입력란에 붙여넣습니다.",
    api_key_billing_note: "API 사용 요금은 Google 계정(본인)에 청구됩니다.",
    btn_show_key: "보기",
    btn_hide_key: "숨기기",
    err_shop_name_required: "먼저 매장명을 입력해 주세요.",
    concept_preview_empty: "매장명을 입력하면 맞춤 예시가 여기에 표시됩니다.",
    concept_load_note: "매장명을 기준으로 컨셉 초안을 채웁니다. 내용은 자유롭게 수정하세요.",
    err_api_key_invalid: "Google AI API 키 형식이 올바르지 않습니다.",
    hero_captions: ["치즈 폭포의 향연!", "겉바속촉의 정석", "오늘 점심은 돈까스?"],
  },
  ja: {
    nav_features: "機能",
    nav_pricing: "料金",
    nav_studio: "スタジオ",
    cta_subscribe: "登録する",
    hero_eyebrow: "サブスク + 自分のGemini APIキー",
    hero_title: "小規模店舗向けAIショート動画",
    hero_lead:
      "店舗情報を入力するだけ。Gemini脚本・Imagen画像・Veo動画・Lyria BGMを9:16素材でお届けします。",
    hero_cta_primary: "料金を見る",
    hero_cta_secondary: "スタジオを開く",
    chip_script: "脚本",
    chip_video: "動画",
    features_title: "世界中の店舗オーナーへ",
    f1_title: "登録してすぐ作成",
    f1_body: "月額でクォータを利用し、自分のGoogle AI APIキーでパイプラインを実行。",
    f2_title: "フルAIパイプライン",
    f2_body: "縦型PR向けの脚本・ビジュアル・モーション・音楽を一括ワークフロー。",
    f3_title: "シーン別アウトプット",
    f3_body: "字幕・ナレーション・シーン素材をCapCutやReelsにそのまま投入。",
    pricing_title: "シンプルな月額プラン",
    pricing_lead: "全プランでパイプライン完備。クォータは請求周期ごとにリセット。",
    plan_popular: "人気",
    plan_per_month: "/月",
    plan_shorts: "本 / 月",
    plan_shorts_daily: "本 / 日",
    plan_unlimited: "無制限",
    plan_free: "無料",
    btn_start_free: "無料で始める",
    plan_subscribe: "登録する",
    payments_paid_soon: "Pro・Businessの決済は準備中です。スターターは無料でご利用いただけます。",
    payments_soon: "決済設定中です。まもなくご利用いただけます。",
    studio_title: "スタジオ",
    studio_lead: "サブスク会員は自分のGoogle AI APIキーでショート動画を作成します。",
    sub_required: "サブスク登録が必要です",
    quota_remaining: "残り {n} / {q}",
    quota_remaining_daily: "本日 残り {n} / {q}",
    quota_unlimited: "無制限",
    form_title: "ショート動画を作成",
    label_api_key: "Google AI APIキー（本人）",
    label_shop: "店舗名",
    label_concept: "コンセプト / 看板メニュー",
    label_concept_badge: "最重要",
    concept_hint: "1行ではなく3〜5文で書くと良いです。",
    concept_example_label: "記入例",
    btn_load_example: "例を読み込む",
    shop_example: "マットンカツ",
    concept_example:
      "済州黒豚の手作りとんかつ専門店。\n看板はサクサクチーズとんかつ（チーズが長く伸びる）。\nランチセット9,900ウォン、団体予約可。\n温かみのあるウッドインテリア、家族・カップルに人気。\nインスタ風ショートで若年層向け。",
    label_style: "動画スタイル",
    label_duration: "長さ",
    btn_generate: "パイプライン実行",
    results_title: "生成結果",
    results_empty: "まだ動画がありません。フォームを入力して実行してください。",
    loading: "AIパイプライン実行中…",
    loading_steps: [
      "Gemini脚本を生成中…",
      "Lyria BGMをレンダリング中…",
      "Imagen画像を生成中…",
      "Veoで変換中…",
      "素材をパッケージ中…",
    ],
    err_subscribe: "有効なサブスクが必要です。先に登録してください。",
    checkout_err: "決済の開始に失敗しました。",
    done: "生成完了",
    scene_rendered: "レンダー完了",
    footer_note: "Google AI搭載 · 小規模店舗PR向け",
    privacy_note: "サーバーには個人情報・APIキーを保存しません。お使いの端末（スマホ・PC）にのみ保存される場合があります。",
    api_key_privacy: "サーバーには保存しません。利便のためこの端末（スマホ・PC）にのみ記憶できます。",
    api_key_guide_title: "Gemini APIキーの取得方法",
    api_key_step1: "Google AI Studio (aistudio.google.com/apikey) を開く。",
    api_key_step2: "Googleアカウントでログイン。",
    api_key_step3: "「Create API key」をクリック。",
    api_key_step4: "キー (AIza...) をコピーして上に貼り付け。",
    api_key_billing_note: "API利用料はご自身のGoogleアカウントに請求されます。",
    btn_show_key: "表示",
    btn_hide_key: "非表示",
    err_shop_name_required: "先に店舗名を入力してください。",
    concept_preview_empty: "店舗名を入力すると、ここに例文が表示されます。",
    concept_load_note: "店舗名に基づく下書きです。内容は自由に編集できます。",
    err_api_key_invalid: "Google AI APIキーの形式が正しくありません。",
    hero_captions: ["とろけるチーズ！", "サクサクジューシー", "今日のランチは？"],
  },
  zh: {
    nav_features: "功能",
    nav_pricing: "定价",
    nav_studio: "工作室",
    cta_subscribe: "订阅",
    hero_eyebrow: "订阅 + 本人的 Gemini API 密钥",
    hero_title: "小微店铺 AI 短视频宣传",
    hero_lead:
      "只需输入店铺信息。我们运行 Gemini 脚本、Imagen 画面、Veo 视频和 Lyria BGM，交付可编辑的 9:16 素材。",
    hero_cta_primary: "查看方案",
    hero_cta_secondary: "打开工作室",
    chip_script: "脚本",
    chip_video: "视频",
    features_title: "为全球店主打造",
    f1_title: "订阅即可创作",
    f1_body: "按月订阅获得配额，使用您自己的 Google AI API 密钥运行流水线。",
    f2_title: "完整 AI 流水线",
    f2_body: "针对竖屏宣传的场景、视觉、动效和音乐一站式工作流。",
    f3_title: "分镜输出",
    f3_body: "字幕、旁白和分镜素材可直接导入 CapCut 或 Reels。",
    pricing_title: "简单月付方案",
    pricing_lead: "所有方案均含完整流水线。配额按账单周期重置。",
    plan_popular: "热门",
    plan_per_month: "/月",
    plan_shorts: "条 / 月",
    plan_shorts_daily: "条 / 日",
    plan_unlimited: "无限",
    plan_free: "免费",
    btn_start_free: "免费开始",
    plan_subscribe: "订阅",
    payments_paid_soon: "Pro 与 Business 支付即将开放。入门版可免费使用。",
    payments_soon: "支付功能配置中，即将开放。",
    studio_title: "工作室",
    studio_lead: "订阅用户使用本人的 Google AI API 密钥生成短视频。",
    sub_required: "需要订阅",
    quota_remaining: "剩余 {n} / {q}",
    quota_remaining_daily: "今日剩余 {n} / {q}",
    quota_unlimited: "无限",
    form_title: "生成短视频",
    label_api_key: "Google AI API 密钥（本人）",
    label_shop: "店铺名称",
    label_concept: "概念 / 招牌菜",
    label_concept_badge: "最重要",
    concept_hint: "建议写 3～5 句话，不要只写一行。",
    concept_example_label: "填写示例",
    btn_load_example: "载入示例",
    shop_example: "味豚炸猪排",
    concept_example:
      "济州黑猪手工炸猪排专门店。\n招牌：外酥里嫩芝士炸猪排（芝士拉丝）。\n午餐套餐 9,900 韩元，可团体预约。\n温馨木质装修，家庭·情侣顾客多。\n用 Instagram 风短视频吸引年轻客群。",
    label_style: "视频风格",
    label_duration: "时长",
    btn_generate: "运行流水线",
    results_title: "生成结果",
    results_empty: "尚无短视频。填写表单并运行流水线。",
    loading: "AI 流水线运行中…",
    loading_steps: [
      "正在生成 Gemini 脚本…",
      "正在渲染 Lyria BGM…",
      "正在生成 Imagen 画面…",
      "正在用 Veo 转换…",
      "正在打包素材…",
    ],
    err_subscribe: "需要有效订阅。请先订阅。",
    checkout_err: "无法启动结账。",
    done: "生成完成",
    scene_rendered: "已渲染",
    footer_note: "由 Google AI 驱动 · 小微店铺宣传",
    privacy_note: "服务器不存储个人信息或 API 密钥，仅可能保存在您的设备（手机·电脑）上。",
    api_key_privacy: "不在服务器保存。为方便使用，可仅在此设备（手机·电脑）上记住。",
    api_key_guide_title: "如何获取 Gemini API 密钥",
    api_key_step1: "打开 Google AI Studio (aistudio.google.com/apikey)。",
    api_key_step2: "使用 Google 账号登录。",
    api_key_step3: "点击「Create API key」。",
    api_key_step4: "复制密钥 (AIza...) 并粘贴到上方。",
    api_key_billing_note: "API 费用由您的 Google 账号承担。",
    btn_show_key: "显示",
    btn_hide_key: "隐藏",
    err_shop_name_required: "请先输入店铺名称。",
    concept_preview_empty: "输入店铺名称后，此处会显示定制示例。",
    concept_load_note: "根据店铺名称生成概念草稿，可自由修改。",
    err_api_key_invalid: "Google AI API 密钥格式不正确。",
    hero_captions: ["芝士瀑布！", "外酥里嫩", "今天午餐吃什么？"],
  },
  es: {
    nav_features: "Funciones",
    nav_pricing: "Precios",
    nav_studio: "Estudio",
    cta_subscribe: "Suscribirse",
    hero_eyebrow: "Suscripción + tu clave Gemini",
    hero_title: "Shorts con IA para negocios locales",
    hero_lead:
      "Introduce los datos de tu negocio. Ejecutamos guiones Gemini, imágenes Imagen, clips Veo y BGM Lyria — entregados en formato 9:16 listo para editar.",
    hero_cta_primary: "Ver planes",
    hero_cta_secondary: "Abrir estudio",
    chip_script: "Guion",
    chip_video: "Vídeo",
    features_title: "Para dueños de negocios en todo el mundo",
    f1_title: "Suscríbete y crea",
    f1_body: "Suscripción mensual para cuota. Ejecuta el pipeline con tu propia clave Google AI.",
    f2_title: "Pipeline completo de IA",
    f2_body: "Guion, visuales, movimiento y música en un flujo optimizado para promos verticales.",
    f3_title: "Salida por escenas",
    f3_body: "Subtítulos, narración y assets por escena listos para CapCut o Reels.",
    pricing_title: "Planes mensuales simples",
    pricing_lead: "Todos los planes incluyen el pipeline completo. La cuota se reinicia cada periodo.",
    plan_popular: "Popular",
    plan_per_month: "/mes",
    plan_shorts: "shorts / mes",
    plan_shorts_daily: "shorts / día",
    plan_unlimited: "Ilimitado",
    plan_free: "Gratis",
    btn_start_free: "Empezar gratis",
    plan_subscribe: "Suscribirse",
    payments_paid_soon: "El pago de Pro y Business llegará pronto. El plan Inicial es gratis.",
    payments_soon: "Los pagos se están configurando. Pronto disponible.",
    studio_title: "Estudio",
    studio_lead: "Los suscriptores generan shorts con su propia clave Google AI.",
    sub_required: "Se requiere suscripción",
    quota_remaining: "Quedan {n} / {q}",
    quota_remaining_daily: "Hoy quedan {n} / {q}",
    quota_unlimited: "Ilimitado",
    form_title: "Generar un short",
    label_api_key: "Clave Google AI (la tuya)",
    label_shop: "Nombre del negocio",
    label_concept: "Concepto / plato estrella",
    label_concept_badge: "Lo más importante",
    concept_hint: "Escribe 3–5 frases, no solo una línea.",
    concept_example_label: "Ejemplo",
    btn_load_example: "Cargar ejemplo",
    shop_example: "Matdon Katsu",
    concept_example:
      "Restaurante de tonkatsu artesanal con cerdo negro de Jeju.\nEspecialidad: tonkatsu con queso crujiente por fuera y jugoso por dentro (queso muy elástico).\nMenú almuerzo 9.900₩, reservas para grupos.\nInterior cálido de madera, popular entre familias y parejas.\nShorts estilo Instagram para público joven.",
    label_style: "Estilo de vídeo",
    label_duration: "Duración",
    btn_generate: "Ejecutar pipeline",
    results_title: "Resultados",
    results_empty: "Aún no hay shorts. Completa el formulario y ejecuta el pipeline.",
    loading: "Ejecutando pipeline de IA…",
    loading_steps: [
      "Generando guion Gemini…",
      "Renderizando BGM Lyria…",
      "Generando imágenes Imagen…",
      "Convirtiendo con Veo…",
      "Empaquetando assets…",
    ],
    err_subscribe: "Se requiere suscripción activa. Suscríbete primero.",
    checkout_err: "No se pudo iniciar el pago.",
    done: "Generación completada",
    scene_rendered: "Renderizado",
    footer_note: "Con Google AI · Para promos de negocios locales",
    privacy_note: "No almacenamos datos personales ni claves API en el servidor. Solo pueden guardarse en tu dispositivo.",
    api_key_privacy: "No se guarda en el servidor. Puede recordarse solo en este dispositivo (móvil o PC).",
    api_key_guide_title: "Cómo obtener una clave Gemini API",
    api_key_step1: "Abre Google AI Studio (aistudio.google.com/apikey).",
    api_key_step2: "Inicia sesión con tu cuenta de Google.",
    api_key_step3: "Haz clic en «Create API key».",
    api_key_step4: "Copia la clave (AIza...) y pégala arriba.",
    api_key_billing_note: "El uso de la API se factura a tu cuenta de Google.",
    btn_show_key: "Mostrar",
    btn_hide_key: "Ocultar",
    err_shop_name_required: "Introduce primero el nombre del negocio.",
    concept_preview_empty: "Escribe el nombre para ver un ejemplo aquí.",
    concept_load_note: "Borrador según el nombre del negocio. Edítalo libremente.",
    err_api_key_invalid: "Formato de clave Google AI API no válido.",
    hero_captions: ["¡Cascada de queso!", "Crujiente por fuera", "¿Menú del día?"],
  },
};

function normalizeLang(code) {
  const c = (code || "").toLowerCase().split("-")[0];
  return SUPPORTED_LANGS.includes(c) ? c : null;
}

/** 브라우저/OS 사용 언어(navigator.languages) */
function browserPreferredLang() {
  const candidates = navigator.languages?.length
    ? [...navigator.languages]
    : [navigator.language || ""];
  for (const raw of candidates) {
    const hit = normalizeLang(raw);
    if (hit) return hit;
  }
  return null;
}

const manualLang = localStorage.getItem("sf_lang_manual") === "1";
let lang =
  (manualLang && normalizeLang(localStorage.getItem("sf_lang"))) ||
  browserPreferredLang() ||
  normalizeLang(cfg.defaultLocale) ||
  "en";

function t(key) {
  const pack = I18N[lang] || I18N.en;
  const val = pack[key];
  if (val !== undefined && val !== null && val !== "") return val;
  const fallback = I18N.en[key];
  if (fallback !== undefined && fallback !== null && fallback !== "") return fallback;
  return "";
}

function htmlLangAttr() {
  if (lang === "zh") return "zh-Hans";
  return lang;
}

function planNameForLocale(el) {
  const map = { ko: "nameKo", en: "nameEn", ja: "nameJa", zh: "nameZh", es: "nameEs" };
  return el.dataset[map[lang] || "nameEn"] || el.dataset.nameEn || "";
}

function updatePlanNames() {
  document.querySelectorAll(".sf-plan-name").forEach((el) => {
    el.textContent = planNameForLocale(el);
  });
}

function applyI18n() {
  lang = normalizeLang(lang) || browserPreferredLang() || "en";
  document.documentElement.lang = htmlLangAttr();
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key === "quota_remaining" || key === "quota_remaining_daily") {
      const n = el.dataset.remaining || "0";
      const q = el.dataset.quota || "0";
      el.textContent = t(key).replace("{n}", n).replace("{q}", q);
      return;
    }
    const val = t(key);
    if (Array.isArray(val)) return;
    if (!val) return;
    el.textContent = val;
  });
  updatePlanNames();
  updateConceptExamplePreview();
  const langSelect = document.getElementById("lang-select");
  if (langSelect) langSelect.value = lang;
}

function updateConceptExamplePreview() {
  const preview = document.getElementById("concept-example-preview");
  if (preview) preview.textContent = t("concept_example") || I18N.ko.concept_example || "";
}

document.getElementById("lang-select")?.addEventListener("change", (e) => {
  lang = normalizeLang(e.target.value) || "en";
  localStorage.setItem("sf_lang", lang);
  localStorage.setItem("sf_lang_manual", "1");
  applyI18n();
});

function csrfHeaders() {
  const headers = { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" };
  if (cfg.csrfToken) headers["X-CSRF-Token"] = cfg.csrfToken;
  return headers;
}

document.querySelectorAll(".sf-checkout-form").forEach((form) => {
  const isFree = form.dataset.free === "1";
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const plan = form.dataset.plan;
    const emailInput = form.querySelector('input[name="email"]');
    const email = emailInput ? emailInput.value.trim() : "";
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const body = isFree ? { plan } : { plan, email };
      const res = await fetch(CHECKOUT_URL, {
        method: "POST",
        headers: csrfHeaders(),
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.code === "api_key_required" ? t("err_api_key") : (data.detail || t("checkout_err")));
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      alert(err.message);
    } finally {
      btn.disabled = !isFree && !cfg.stripeEnabled;
    }
  });
});

const form = document.getElementById("generate-form");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingStep = document.getElementById("loading-step");
const resultsEmpty = document.getElementById("results-empty");
const resultsPanel = document.getElementById("results-panel");
const statusBanner = document.getElementById("status-banner");
const metaRow = document.getElementById("meta-row");
const sceneList = document.getElementById("scene-list");
const submitBtn = document.getElementById("submit-btn");
const apiKeyInput = document.getElementById("api-key");
const toggleKeyBtn = document.getElementById("toggle-key");
const businessNameInput = document.getElementById("business-name");
const businessConceptInput = document.getElementById("business-concept");
const SHOP_DRAFT_KEY = "sf_shop_draft";

function loadShopDraft() {
  try {
    const data = JSON.parse(localStorage.getItem(SHOP_DRAFT_KEY));
    if (data) {
      if (businessNameInput && data.name) businessNameInput.value = data.name;
      if (businessConceptInput && data.concept) {
        const example = t("concept_example") || I18N.ko.concept_example || "";
        if (data.concept === example) {
          businessConceptInput.value = "";
        } else {
          businessConceptInput.value = data.concept;
        }
      }
    }
  } catch (e) {}
}

function saveShopDraft() {
  if (!businessNameInput || !businessConceptInput) return;
  localStorage.setItem(
    SHOP_DRAFT_KEY,
    JSON.stringify({
      name: businessNameInput.value.trim(),
      concept: businessConceptInput.value.trim(),
    })
  );
}

// 예시 불러오기 기능 삭제

if (apiKeyInput) {
  const savedKey = localStorage.getItem("sf_gemini_key");
  if (savedKey) apiKeyInput.value = savedKey;
}

loadShopDraft();

document.getElementById("load-concept-example")?.addEventListener("click", loadConceptExample);
businessNameInput?.addEventListener("blur", saveShopDraft);
businessConceptInput?.addEventListener("blur", saveShopDraft);

toggleKeyBtn?.addEventListener("click", () => {
  const show = apiKeyInput.type === "password";
  apiKeyInput.type = show ? "text" : "password";
  toggleKeyBtn.textContent = t(show ? "btn_hide_key" : "btn_show_key");
});

let loadingInterval = null;
let phoneRotateInterval = null;

form?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const apiKey = apiKeyInput?.value.trim() || "";
  if (!apiKey) {
    showError(t("err_api_key"));
    return;
  }
  if (!/^AIza[0-9A-Za-z_-]{20,}$/.test(apiKey)) {
    showError(t("err_api_key_invalid"));
    return;
  }

  const payload = {
    credentials: { api_key: apiKey },
    business_name: document.getElementById("business-name").value.trim(),
    business_concept: document.getElementById("business-concept").value.trim(),
    video_style: document.getElementById("video-style").value,
    duration_seconds: parseInt(document.getElementById("duration").value, 10),
  };

  if (!payload.business_name || !payload.business_concept) {
    showError(t("label_shop") + " / " + t("label_concept"));
    return;
  }

  startLoading();
  submitBtn.disabled = true;

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: csrfHeaders(),
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      if (data.code === "api_key_required") {
        throw new Error(t("err_api_key"));
      }
      if (res.status === 402 || res.status === 403) {
        throw new Error(data.detail || t("err_subscribe"));
      }
      throw new Error(data.detail || "Server error");
    }

    showResults(data);
    startPhonePreview(data.assets?.timeline_scenes || []);
    refreshSubscription();
    if (apiKey) localStorage.setItem("sf_gemini_key", apiKey);
    saveShopDraft();
  } catch (err) {
    showError(err.message);
  } finally {
    stopLoading();
    submitBtn.disabled = false;
  }
});

function startLoading() {
  const steps = t("loading_steps");
  const LOADING_STEPS = Array.isArray(steps) ? steps : I18N.en.loading_steps;
  loadingOverlay.classList.add("visible");
  let step = 0;
  loadingStep.textContent = LOADING_STEPS[0];
  loadingInterval = setInterval(() => {
    step = (step + 1) % LOADING_STEPS.length;
    loadingStep.textContent = LOADING_STEPS[step];
  }, 1800);
}

function stopLoading() {
  loadingOverlay.classList.remove("visible");
  clearInterval(loadingInterval);
}

function showError(message) {
  resultsEmpty.style.display = "none";
  resultsPanel.classList.add("visible");
  statusBanner.className = "sf-status err";
  statusBanner.textContent = message;
  metaRow.innerHTML = "";
  sceneList.innerHTML = "";
}

function showResults(data) {
  resultsEmpty.style.display = "none";
  resultsPanel.classList.add("visible");
  statusBanner.className = "sf-status ok";
  statusBanner.textContent = data.message || t("done");

  const meta = data.meta || {};
  metaRow.innerHTML = `
    <span>${escapeHtml(meta.business_name || "")}</span>
    <span>${escapeHtml(meta.style || "")}</span>
    <span>${meta.total_duration || 0}s</span>
    <span>BGM</span>
  `;

  const scenes = data.assets?.timeline_scenes || [];
  sceneList.innerHTML = scenes
    .map(
      (scene) => `
    <div class="sf-scene-card">
      <div class="sf-scene-head">
        <span class="sf-scene-num">Scene ${scene.scene_number}</span>
        <span class="sf-scene-badge">${t("scene_rendered")}</span>
      </div>
      <div class="sf-scene-caption">${escapeHtml(scene.caption)}</div>
      <div class="sf-scene-narration">${escapeHtml(scene.narration)}</div>
    </div>
  `
    )
    .join("");
}

function startPhonePreview(scenes) {
  const screen = document.getElementById("phone-screen");
  if (!screen || !scenes.length) return;

  clearInterval(phoneRotateInterval);

  screen.innerHTML = scenes
    .map(
      (s, i) => `
    <div class="sf-phone-scene${i === 0 ? " active" : ""}">Scene ${s.scene_number}</div>
  `
    )
    .join(`
    <div class="sf-phone-caption" id="phone-caption">${escapeHtml(scenes[0].caption)}</div>
  `);

  let current = 0;
  const phoneScenes = screen.querySelectorAll(".sf-phone-scene");
  const captionEl = document.getElementById("phone-caption");

  phoneRotateInterval = setInterval(() => {
    phoneScenes[current]?.classList.remove("active");
    current = (current + 1) % scenes.length;
    phoneScenes[current]?.classList.add("active");
    if (captionEl) captionEl.textContent = scenes[current].caption;
  }, 3000);
}

async function refreshSubscription() {
  try {
    const res = await fetch(SUB_URL, { credentials: "same-origin" });
    const data = await res.json();
    updateSubStatus(data.subscription);
  } catch (_) {
    /* ignore */
  }
}

function updateSubStatus(sub) {
  const el = document.getElementById("sub-status");
  if (!el) return;
  if (sub && sub.active) {
    el.className = "sf-sub-status sf-sub-active";
    const planEl = document.querySelector(`.sf-plan-name[data-plan-id="${sub.plan}"]`);
    const planLabel = planEl ? planNameForLocale(planEl) : escapeHtml(sub.plan_name || sub.plan);
    const quotaKey =
      sub.limit_type === "unlimited"
        ? "quota_unlimited"
        : sub.limit_type === "daily"
          ? "quota_remaining_daily"
          : "quota_remaining";
    const quotaAttrs =
      sub.limit_type === "unlimited"
        ? ""
        : ` data-remaining="${sub.remaining}" data-quota="${sub.quota}"`;
    el.innerHTML = `
      <span class="sf-sub-plan">${planLabel}</span>
      <span class="sf-sub-quota" data-i18n="${quotaKey}"${quotaAttrs}></span>
    `;
    applyI18n();
  } else {
    el.className = "sf-sub-status";
    el.innerHTML = `<span data-i18n="sub_required"></span>`;
    applyI18n();
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

(function initHeroDemo() {
  const captionEl = document.getElementById("hero-caption");
  const scenes = document.querySelectorAll("#hero-phone .sf-phone-scene");
  if (!scenes.length) return;

  let idx = 0;
  setInterval(() => {
    const list = t("hero_captions");
    const captions = Array.isArray(list) ? list : I18N.en.hero_captions;
    scenes[idx]?.classList.remove("active");
    idx = (idx + 1) % scenes.length;
    scenes[idx]?.classList.add("active");
    if (captionEl) captionEl.textContent = captions[idx % captions.length];
  }, 2800);
})();

applyI18n();

if (window.location.hash) {
  const target = document.querySelector(window.location.hash);
  target?.scrollIntoView({ behavior: "smooth" });
}
