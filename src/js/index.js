
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
import AppConsentForm from './components/app-consent-form';
import AppAuthorizationsTable from './components/app-authorizations-table';
import CreateTokenForm from './components/create-token-form';
import TokensTable from './components/tokens-table';

Vue.use(Buefy);

window.APP_MOUNTED_EVENT = 'app_mounted';
window.onload = function () {
    window.app = new Vue({
        el: '#app',
        components: {
            'login-form': LoginForm,
            'init-form': InitForm,
            'jobs-table': JobsTable,
            'app-consent-form': AppConsentForm,
            'app-authorizations-table': AppAuthorizationsTable,
            'create-token-form': CreateTokenForm,
            'tokens-table': TokensTable,

        },
        created: function () {
        },
        mounted: function () {
            window.dispatchEvent(new CustomEvent(window.APP_MOUNTED_EVENT, {detail: this}));
        }
    });
}

