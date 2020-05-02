
require('material-icons/iconfont/material-icons.css');
require('@fortawesome/fontawesome-free/css/all.css');
require('@fortawesome/fontawesome-free/js/all.js');

require('./admin-one');


import Vue from 'vue';
import Buefy from 'buefy';

require('../css/style.scss');
require('../img/logo-full.png');

import LoginForm from './components/login-form';
import JobsTable from './components/jobs-table';
import InitForm from './components/init-form';
import AuthorizeAppForm from './components/authorize-app-form';
import AuthorizedAppsTable from './components/authorized-apps-table';

Vue.use(Buefy);

window.onload = function () {
    window.app = new Vue({
        el: '#app',
        components: {
            'login-form': LoginForm,
            'init-form': InitForm,
            'jobs-table': JobsTable,
            'authorize-app-form': AuthorizeAppForm,
            'authorized-apps-table': AuthorizedAppsTable,

        },
        created: function () {
        },
        mounted: function () {
        }
    });
}

