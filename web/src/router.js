import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Opportunities from './views/Opportunities.vue'
import OpportunityDetail from './views/OpportunityDetail.vue'
import CalendarView from './views/Calendar.vue'
import Review from './views/Review.vue'
import Settings from './views/Settings.vue'
import Onboarding from './views/Onboarding.vue'

const routes = [
  { path: '/', name: 'dashboard', component: Dashboard, meta: { title: '仪表盘', subtitle: '今天要面什么、有什么要回' } },
  { path: '/opportunities', name: 'opportunities', component: Opportunities, meta: { title: '机会', subtitle: '所有投递与进展' } },
  { path: '/opportunities/:id', name: 'opportunity', component: OpportunityDetail, meta: { title: '机会详情', subtitle: '完整时间线与依据' } },
  { path: '/calendar', name: 'calendar', component: CalendarView, meta: { title: '日历', subtitle: '面试、测评与截止时间' } },
  { path: '/review', name: 'review', component: Review, meta: { title: '审核队列', subtitle: '低置信度的邮件，需要你拍板' } },
  { path: '/settings', name: 'settings', component: Settings, meta: { title: '设置', subtitle: '邮箱、AI 与本地数据' } },
  { path: '/onboarding', name: 'onboarding', component: Onboarding, meta: { title: '开始使用', subtitle: '三步完成配置', bare: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

export default router
