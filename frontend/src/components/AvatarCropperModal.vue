<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: Boolean,
  imageSrc: String,
  title: {
    type: String,
    default: '自訂頭像照片裁切',
  },
})

const emit = defineEmits(['close', 'crop'])

// 視窗與 ROI 圓圈常數
const VIEWPORT_SIZE = 280 // 取景框大小 280x280 px
const ROI_DIAMETER = 220 // 圓形 ROI 直徑 220 px
const ROI_RADIUS = ROI_DIAMETER / 2 // 110 px

// 影像原始尺寸與載入狀態
const imgRef = ref(null)
const naturalWidth = ref(0)
const naturalHeight = ref(0)
const imageLoaded = ref(false)

// 座標平移與縮放狀態
const scale = ref(1.0)
const minScale = ref(1.0)
const maxScale = ref(3.5)
const offsetX = ref(0)
const offsetY = ref(0)

// 底圖基本顯示尺寸 (當 scale = 1 時剛好填滿 ROI 圓圈)
const baseWidth = ref(ROI_DIAMETER)
const baseHeight = ref(ROI_DIAMETER)

// 手勢與拖曳狀態
const isDragging = ref(false)
const activePointers = new Map()
let lastPinchDistance = 0

// 計算最大平移限制 (避免照片移出 ROI 圓圈造成留白)
const maxOffsetX = computed(() => {
  const currentW = baseWidth.value * scale.value
  return Math.max(0, currentW / 2 - ROI_RADIUS)
})

const maxOffsetY = computed(() => {
  const currentH = baseHeight.value * scale.value
  return Math.max(0, currentH / 2 - ROI_RADIUS)
})

function clampOffsets() {
  offsetX.value = Math.max(-maxOffsetX.value, Math.min(maxOffsetX.value, offsetX.value))
  offsetY.value = Math.max(-maxOffsetY.value, Math.min(maxOffsetY.value, offsetY.value))
}

// 監聽縮放滑桿變化，自動校正邊界
watch(scale, () => {
  clampOffsets()
})

// 當傳入新圖片時重新初始化
watch(
  () => props.imageSrc,
  (newSrc) => {
    if (newSrc && props.show) {
      loadImage(newSrc)
    }
  },
  { immediate: true }
)

watch(
  () => props.show,
  (newVal) => {
    if (newVal && props.imageSrc) {
      loadImage(props.imageSrc)
    }
  }
)

function loadImage(src) {
  imageLoaded.value = false
  const img = new Image()
  if (src.startsWith('http://') || src.startsWith('https://')) {
    img.crossOrigin = 'anonymous'
  }
  img.onload = () => {
    naturalWidth.value = img.naturalWidth || 1
    naturalHeight.value = img.naturalHeight || 1

    // 依長寬比計算底圖在 scale = 1 時剛好覆蓋 ROI 圓圈的尺寸
    const aspect = naturalWidth.value / naturalHeight.value
    if (aspect >= 1) {
      // 橫式相片：以高度為基準填滿 ROI 直徑
      baseHeight.value = ROI_DIAMETER
      baseWidth.value = ROI_DIAMETER * aspect
    } else {
      // 直式相片：以寬度為基準填滿 ROI 直徑
      baseWidth.value = ROI_DIAMETER
      baseHeight.value = ROI_DIAMETER / aspect
    }

    scale.value = 1.0
    minScale.value = 1.0
    offsetX.value = 0
    offsetY.value = 0
    imageLoaded.value = true
  }
  img.onerror = () => {
    if (img.crossOrigin) {
      const fallbackImg = new Image()
      fallbackImg.onload = () => {
        naturalWidth.value = fallbackImg.naturalWidth || 1
        naturalHeight.value = fallbackImg.naturalHeight || 1
        const aspect = naturalWidth.value / naturalHeight.value
        if (aspect >= 1) {
          baseHeight.value = ROI_DIAMETER
          baseWidth.value = ROI_DIAMETER * aspect
        } else {
          baseWidth.value = ROI_DIAMETER
          baseHeight.value = ROI_DIAMETER / aspect
        }
        scale.value = 1.0
        minScale.value = 1.0
        offsetX.value = 0
        offsetY.value = 0
        imageLoaded.value = true
      }
      fallbackImg.src = src
    } else {
      console.error('裁切器圖片載入失敗:', src)
    }
  }
  img.src = src
}

// 指針拖曳事件 (支援手機觸控與桌機滑鼠)
function handlePointerDown(e) {
  if (!imageLoaded.value) return
  const target = e.currentTarget
  target.setPointerCapture(e.pointerId)
  activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  isDragging.value = true

  if (activePointers.size === 2) {
    const pts = Array.from(activePointers.values())
    lastPinchDistance = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
  }
}

function handlePointerMove(e) {
  if (!isDragging.value || !activePointers.has(e.pointerId)) return

  // 雙指縮放 (Pinch-to-zoom)
  if (activePointers.size === 2) {
    activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
    const pts = Array.from(activePointers.values())
    const currentDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
    if (lastPinchDistance > 0 && currentDist > 0) {
      const zoomFactor = currentDist / lastPinchDistance
      scale.value = Math.max(minScale.value, Math.min(maxScale.value, scale.value * zoomFactor))
      clampOffsets()
    }
    lastPinchDistance = currentDist
    return
  }

  // 單指 / 滑鼠拖曳移動
  const prev = activePointers.get(e.pointerId)
  const deltaX = e.clientX - prev.x
  const deltaY = e.clientY - prev.y

  offsetX.value += deltaX
  offsetY.value += deltaY
  clampOffsets()

  activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
}

function handlePointerUp(e) {
  activePointers.delete(e.pointerId)
  if (activePointers.size === 0) {
    isDragging.value = false
    lastPinchDistance = 0
  }
}

// 滑鼠滾輪縮放
function handleWheel(e) {
  e.preventDefault()
  if (!imageLoaded.value) return
  const step = e.deltaY < 0 ? 0.08 : -0.08
  scale.value = Math.max(minScale.value, Math.min(maxScale.value, Number((scale.value + step).toFixed(2))))
  clampOffsets()
}

// 快速按鈕縮放
function zoomIn() {
  scale.value = Math.min(maxScale.value, Number((scale.value + 0.15).toFixed(2)))
  clampOffsets()
}

function zoomOut() {
  scale.value = Math.max(minScale.value, Number((scale.value - 0.15).toFixed(2)))
  clampOffsets()
}

function handleReset() {
  scale.value = 1.0
  offsetX.value = 0
  offsetY.value = 0
}

// 核心 Canvas 截取邏輯
function handleConfirmCrop() {
  if (!imageLoaded.value || !imgRef.value) return

  const canvas = document.createElement('canvas')
  const outSize = 512 // 512x512 高解析度方形輸出
  canvas.width = outSize
  canvas.height = outSize
  const ctx = canvas.getContext('2d')

  // 計算底圖當前渲染尺寸
  const currentRenderW = baseWidth.value * scale.value
  const currentRenderH = baseHeight.value * scale.value

  // ROI 圓心位於取景框中央 (VIEWPORT_SIZE / 2)
  // ROI 左上角相對於底圖左上角的像素偏移
  const cropLeftInRendered = currentRenderW / 2 - ROI_RADIUS - offsetX.value
  const cropTopInRendered = currentRenderH / 2 - ROI_RADIUS - offsetY.value

  // 轉換為原始影像解析度之座標與長寬
  const renderToNaturalRatio = naturalWidth.value / currentRenderW
  const sourceX = Math.max(0, cropLeftInRendered * renderToNaturalRatio)
  const sourceY = Math.max(0, cropTopInRendered * renderToNaturalRatio)
  const sourceSize = ROI_DIAMETER * renderToNaturalRatio

  // 將選取區域以高畫質平滑繪製至 Canvas
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(
    imgRef.value,
    sourceX,
    sourceY,
    sourceSize,
    sourceSize,
    0,
    0,
    outSize,
    outSize
  )

  canvas.toBlob(
    (blob) => {
      if (!blob) return
      const dataUrl = canvas.toDataURL('image/webp', 0.95)
      const croppedFile = new File([blob], 'cropped_avatar.webp', { type: 'image/webp' })
      emit('crop', { blob, dataUrl, file: croppedFile })
      emit('close')
    },
    'image/webp',
    0.95
  )
}
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-md select-none touch-none"
    @keydown.esc="emit('close')"
  >
    <div
      class="bg-white rounded-3xl shadow-2xl max-w-sm sm:max-w-md w-full p-5 sm:p-6 text-center animate-in fade-in zoom-in duration-200 border border-gray-100"
    >
      <!-- 標題欄 -->
      <div class="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
        <div class="text-left">
          <h3 class="text-base sm:text-lg font-black text-gray-900 tracking-tight flex items-center space-x-1.5">
            <span>✂️</span>
            <span>{{ title }}</span>
          </h3>
          <p class="text-[11px] text-gray-500 mt-0.5">
            拖曳移動相片，使用滾輪或滑桿縮放至最佳頭像視野
          </p>
        </div>
        <button
          type="button"
          @click="emit('close')"
          class="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 flex items-center justify-center text-sm font-bold transition cursor-pointer"
        >
          ✕
        </button>
      </div>

      <!-- 取景視窗 (Viewport) -->
      <div
        class="relative mx-auto overflow-hidden rounded-2xl bg-gray-950 border-2 border-gray-800 shadow-inner cursor-grab active:cursor-grabbing flex items-center justify-center"
        :style="{ width: `${VIEWPORT_SIZE}px`, height: `${VIEWPORT_SIZE}px` }"
        @pointerdown="handlePointerDown"
        @pointermove="handlePointerMove"
        @pointerup="handlePointerUp"
        @pointercancel="handlePointerUp"
        @wheel.prevent="handleWheel"
      >
        <!-- 待裁切影像層 (硬體加速轉換) -->
        <img
          v-show="imageLoaded"
          ref="imgRef"
          :src="imageSrc"
          alt="Cropper Source"
          draggable="false"
          class="absolute max-w-none pointer-events-none select-none transition-none will-change-transform"
          :style="{
            width: `${baseWidth}px`,
            height: `${baseHeight}px`,
            transform: `translate3d(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px), 0) scale(${scale})`,
            transformOrigin: 'center center',
            left: '50%',
            top: '50%',
          }"
        />

        <!-- ROI 圓圈透明遮罩層 (利用大 box-shadow 遮蔽外圍) -->
        <div class="absolute inset-0 pointer-events-none flex items-center justify-center">
          <div
            class="rounded-full border-2 border-white/90 shadow-[0_0_0_9999px_rgba(0,0,0,0.65)] relative flex items-center justify-center"
            :style="{ width: `${ROI_DIAMETER}px`, height: `${ROI_DIAMETER}px` }"
          >
            <!-- 圓心微光十字參考線 -->
            <div class="absolute w-3 h-0.5 bg-white/40 pointer-events-none"></div>
            <div class="absolute h-3 w-0.5 bg-white/40 pointer-events-none"></div>

            <!-- 圓圈底部提示標籤 -->
            <div class="absolute -bottom-7 bg-black/60 text-white/90 text-[10px] px-2.5 py-0.5 rounded-full font-medium tracking-wider backdrop-blur-xs">
              頭像圓形視野 (ROI)
            </div>
          </div>
        </div>

        <!-- 載入中骨架提示 -->
        <div v-if="!imageLoaded" class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs">
          <span>相片載入中...</span>
        </div>
      </div>

      <!-- 控制欄位：縮放滑桿與重設 -->
      <div class="mt-4 space-y-3">
        <!-- 縮放控制條 -->
        <div class="flex items-center space-x-2 bg-gray-50 p-2.5 rounded-2xl border border-gray-100">
          <button
            type="button"
            @click="zoomOut"
            class="w-7 h-7 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-700 shadow-xs cursor-pointer transition"
            title="縮小"
          >
            ➖
          </button>

          <input
            type="range"
            :min="minScale"
            :max="maxScale"
            step="0.01"
            v-model.number="scale"
            class="flex-1 accent-frog-600 h-1.5 bg-gray-200 rounded-lg cursor-pointer"
          />

          <button
            type="button"
            @click="zoomIn"
            class="w-7 h-7 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-700 shadow-xs cursor-pointer transition"
            title="放大"
          >
            ➕
          </button>

          <span class="text-xs font-mono font-bold text-frog-700 w-12 text-right">
            {{ Math.round((scale / minScale) * 100) }}%
          </span>
        </div>

        <!-- 操作按鈕列 -->
        <div class="flex items-center space-x-2 pt-1">
          <button
            type="button"
            @click="handleReset"
            class="py-2.5 px-3 rounded-xl border border-gray-200 hover:bg-gray-50 text-gray-600 font-bold text-xs transition cursor-pointer flex items-center space-x-1"
            title="將相片恢復預設置中"
          >
            <span>🔄</span>
            <span>重設</span>
          </button>

          <button
            type="button"
            @click="emit('close')"
            class="flex-1 py-2.5 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 font-bold text-xs transition cursor-pointer"
          >
            取消
          </button>

          <button
            type="button"
            @click="handleConfirmCrop"
            :disabled="!imageLoaded"
            class="flex-1 py-2.5 rounded-xl bg-frog-500 hover:bg-frog-600 text-white font-bold text-xs shadow-md shadow-frog-200 transition disabled:opacity-50 cursor-pointer flex items-center justify-center space-x-1"
          >
            <span>✂️</span>
            <span>確認裁切</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
