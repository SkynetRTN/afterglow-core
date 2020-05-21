<template>
  <div class="container">
    <div v-if="icon" class="content">
       <img class="image" v-bind:src="icon" style="max-width: 125px; max-height: 125px; margin: auto;">
    </div>
    
    <p class="content"><b>{{name}}</b> is a third-party application which would like access to parts of your Afterglow Core account.  Only grant this access if you trust the third-party application with your information and data</p>
  
    <p class="content">{{description}}</p>

    <form id="init-form" method="post" @submit="formSubmit">
      <div class="field is-grouped is-grouped-right">
        <div class="control">
          <a class="button is-link is-light" href="/">Deny</a>
        </div>
        <div class="control">
          <button
            class="button is-link"
            :disabled="submitDisabled"
            v-bind:class="{ 'is-loading': loading }"
          >Allow</button>
        </div>
      </div>
    </form>
  </div>
</template>

<script>
import axios from "axios";
import {config} from '../config';
import {coreService} from '../services'

export default {
  data: function() {
    return {
      loading: false,
      errors: []
    };
  },
  props: ["nextUrl", "id", "name", "description", "icon"],
  methods: {
    formSubmit: function(e) {
      e.preventDefault();

      this.loading=true;
      this.errors = [];
      
      coreService.createAppAuthorization(this.id)
      .then((response) => {
        if (this.nextUrl) {
          window.location = this.nextUrl;
        } else {
          window.location = "/";
        }
      })
      .catch((error) => {
        this.errors = [];
        var r = error.response;
        switch (r.status) {
          case 500: {
            this.errors.push("An unexpected error occurred");
            break;
          }
          case 400: {
            if (typeof r.data == "string") {
              this.errors.push(r.data);
            } else {
              for (var field in r.data) {
                if (Array.isArray(r.data[field])) {
                  r.data[field].forEach(e => this.errors.push(e));
                } else {
                  this.errors.push(r.data[field]);
                }
              }
            }

            break;
          }
          default: {
            this.errors.push("An unexpected error occurred");
            break;
          }
        }
      })
      .finally(() => {
        this.loading = false;
      });
      

      return;
    }
  },
  computed: {
    submitDisabled: function() {
      return this.loading;
    }
  }
};
</script>