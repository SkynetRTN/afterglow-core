/* Styles */
import './scss/main.scss'

/* Core */
import Vue from 'vue'
import Buefy from 'buefy'

import App from './App.vue'
import store from './store'
import router from './router'
import VueClipboard from 'vue-clipboard2'
import './permission'

/* Service Worker */
import './registerServiceWorker'

Vue.config.productionTip = false
Vue.use(Buefy)
Vue.use(VueClipboard);
new Vue({
  router,
  store,
  render: (h) => h(App)
}).$mount('#app')
