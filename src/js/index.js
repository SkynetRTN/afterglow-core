
require('material-icons/iconfont/material-icons.css');
require('@fortawesome/fontawesome-free/css/all.css');
require('@fortawesome/fontawesome-free/js/all.js');


import Vue from 'vue';

require('../css/style.scss');
require('../img/logo-full.png');

require('../plugins/index');

import LoginForm from './components/login-form';


window.onload = function () {
    new Vue({
        el: '#app',
        components: {
            'login-form': LoginForm,
        },
        created: function () {
        }
    });
}

