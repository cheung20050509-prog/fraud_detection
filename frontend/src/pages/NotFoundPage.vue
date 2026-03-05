<template>
  <div class="min-h-screen bg-gray-50">
    <div class="max-w-4xl mx-auto px-4 py-8">
      <div class="text-center">
        <div class="mb-8">
          <div class="w-24 h-24 bg-gray-200 rounded-full flex items-center justify-center mx-auto">
            <Search class="h-12 w-12 text-gray-400" />
          </div>
        </div>
        <h1 class="text-4xl font-bold text-gray-900 mb-4">页面未找到</h1>
        <p class="text-xl text-gray-600 mb-8">抱歉，您访问的页面不存在</p>
        
        <div class="space-y-4">
          <router-link to="/"
                     class="inline-flex items-center px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors">
            <Home class="h-5 w-5 mr-2" />
            返回首页
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Home, Search } from 'lucide-vue-next'
</script>