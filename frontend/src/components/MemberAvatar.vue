<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  avatar: {
    type: String,
    default: '🐸',
  },
  size: {
    type: String,
    default: 'md', // 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | 'custom'
  },
  alt: {
    type: String,
    default: '',
  },
  shape: {
    type: String,
    default: 'circle', // 'circle' | 'rounded'
  },
})

const imgError = ref(false)

watch(
  () => props.avatar,
  () => {
    imgError.value = false
  }
)

const isImage = computed(() => {
  if (imgError.value) return false
  if (!props.avatar) return false
  const a = props.avatar.trim()
  return (
    a.startsWith('/') ||
    a.startsWith('http://') ||
    a.startsWith('https://') ||
    a.startsWith('data:image')
  )
})

const sizeClasses = {
  xs: 'w-5 h-5 text-xs',
  sm: 'w-7 h-7 text-sm',
  md: 'w-9 h-9 text-base',
  lg: 'w-12 h-12 text-2xl',
  xl: 'w-16 h-16 text-3xl',
  '2xl': 'w-20 h-20 text-4xl',
  '3xl': 'w-24 h-24 text-5xl',
  custom: '',
}

const shapeClasses = {
  circle: 'rounded-full',
  rounded: 'rounded-2xl',
}

function handleImgError() {
  imgError.value = true
}
</script>

<template>
  <div
    class="relative inline-flex items-center justify-center flex-shrink-0 overflow-hidden select-none"
    :class="[
      sizeClasses[size] || sizeClasses.md,
      shapeClasses[shape] || shapeClasses.circle,
      isImage ? 'border border-black/10 shadow-xs bg-gray-100' : '',
    ]"
    :title="alt"
  >
    <img
      v-if="isImage"
      :src="avatar"
      :alt="alt || '頭像'"
      class="w-full h-full object-cover"
      :class="shapeClasses[shape] || shapeClasses.circle"
      @error="handleImgError"
      loading="lazy"
    />
    <span v-else class="leading-none flex items-center justify-center transform scale-100">
      {{ avatar || '🐸' }}
    </span>
  </div>
</template>
