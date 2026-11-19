<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getCaptchaApi } from '@/api/auth'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const captchaImage = ref('')
const captchaEnabled = ref(true)

const form = reactive({
  username: 'admin',
  password: 'admin123',
  captcha_key: '',
  captcha_code: '',
})

const rules = computed<FormRules>(() => ({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  ...(captchaEnabled.value
    ? { captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }] }
    : {}),
}))

async function refreshCaptcha() {
  const res = await getCaptchaApi()
  captchaEnabled.value = res.enabled !== false
  if (!captchaEnabled.value) {
    captchaImage.value = ''
    form.captcha_key = ''
    form.captcha_code = ''
    return
  }
  captchaImage.value = res.captcha_image
  form.captcha_key = res.captcha_key
  form.captcha_code = ''
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await userStore.login({ ...form })
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(refreshCaptcha)
</script>

<template>
  <div class="login-page">
    <div class="login-decor decor-1" />
    <div class="login-decor decor-2" />

    <div class="login-box">
      <div class="login-brand">
        <el-icon class="brand-icon"><Lightning /></el-icon>
        <h1>绿色低碳智慧管控系统</h1>
        <p>省能 · 省钱 · 合规 · 安全</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="'User'" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="'Lock'"
            show-password
          />
        </el-form-item>
        <el-form-item v-if="captchaEnabled" prop="captcha_code">
          <div class="captcha-row">
            <el-input v-model="form.captcha_code" placeholder="请输入验证码" :prefix-icon="'Key'" />
            <img class="captcha-img" :src="captchaImage" alt="验证码" title="点击刷新" @click="refreshCaptcha" />
          </div>
        </el-form-item>
        <el-button class="login-btn" type="primary" size="large" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>

      <p class="login-tip">默认账号：admin / admin123</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(135deg, #06152f 0%, #0b3a86 55%, #1677ff 100%);
}

.login-decor {
  position: absolute;
  border-radius: 50%;
  filter: blur(6px);
  opacity: 0.35;
}

.decor-1 {
  width: 520px;
  height: 520px;
  top: -180px;
  left: -140px;
  background: radial-gradient(circle, rgba(22, 119, 255, 0.9), transparent 70%);
}

.decor-2 {
  width: 620px;
  height: 620px;
  right: -200px;
  bottom: -220px;
  background: radial-gradient(circle, rgba(0, 185, 107, 0.7), transparent 70%);
}

.login-box {
  position: relative;
  z-index: 2;
  width: 420px;
  padding: 40px 36px 28px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(2, 18, 45, 0.45);
}

.login-brand {
  text-align: center;
  margin-bottom: 26px;

  .brand-icon {
    font-size: 44px;
    color: $primary-color;
  }

  h1 {
    margin: 12px 0 6px;
    font-size: 21px;
    color: #0b1e3d;
    letter-spacing: 1px;
  }

  p {
    margin: 0;
    font-size: 13px;
    color: $text-secondary;
    letter-spacing: 4px;
  }
}

.captcha-row {
  display: flex;
  width: 100%;
  gap: 10px;

  .el-input {
    flex: 1;
  }

  .captcha-img {
    width: 120px;
    height: 40px;
    border-radius: 6px;
    cursor: pointer;
    object-fit: cover;
  }
}

.login-btn {
  width: 100%;
  letter-spacing: 6px;
  margin-top: 4px;
}

.login-tip {
  margin: 18px 0 0;
  text-align: center;
  font-size: 12px;
  color: $text-secondary;
}
</style>
