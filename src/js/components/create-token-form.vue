<template>
  <section>
      <form id="create-token-form" method="post" @submit="formSubmit">
      <div class="notification is-danger" v-if="errors.length">
        <ul>
          <li v-for="error in errors" v-bind:key="error">{{ error }}</li>
        </ul>
      </div>

      <div class="field">
        <label for="note" class="label">Note</label>
        <div class="control has-icons-left">
          <input id="note" name="note" v-model="note" type="text" value class="input" placeholder="What’s this token for?"  />
          <span class="icon is-small is-left">
            <i class="fas fa-sticky-note"></i>
          </span>
        </div>
      </div>
      
      <div class="field is-grouped is-grouped-right">
        <div class="control">
          <button
            class="button is-link"
            :disabled="submitDisabled"
            v-bind:class="{ 'is-loading': loading }"
          >Create</button>
        </div>
      </div>
    </form>
      <b-modal :active.sync="showTokenModal"
            has-modal-card
            trap-focus
            :destroy-on-hide="true"
            aria-role="dialog"
            aria-modal>
      <token-modal :token="token"></token-modal>
  </b-modal>
  </section>
  
</template>

<script>
import { coreService } from "../services";
import * as ClipboardJS from "clipboard";



const TokenModal = {
        props: ['token'],
        template: `
          <div class="modal-card" style="width: auto">
          <section class="modal-card-body">
            <div class="container">
                <div class="content">
                    <p>A personal access token was successfully created.  You will only be able to view the token once so be sure to copy it now before closing this dialog window.</p>
                    <div class="field has-addons">
                        <div class="control is-expanded">
                            <input id="access_token" class="input" type="text" :value="token.access_token" readonly>
                        </div>
                        <div class="control">
                            <button class="button is-info" data-clipboard-target="#access_token" alt="Copy to clipboard">
                                <span class="icon is-small">
                                <i class="fas fa-copy"></i>
                                </span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
          </section>
          </div>
        `,
        mounted () {
          new ClipboardJS('.button');
        }

    }

export default {
  components: {
      TokenModal
  },
  data: function() {
    return {
      note: null,
      loading: false,
      errors: [],
      token: null,
      showTokenModal: false
    };
  },
  props: ["cancelUrl"],
  methods: {
    formSubmit: function(e) {
      e.preventDefault();

      this.errors = [];

      if (!this.note) {
        this.errors.push("A note is required.");
      }
     
      if (this.errors.length == 0) {
        this.loading = true;
        coreService
          .createToken({
              note: this.note
          })
          .then((resp) => {
            this.note = '';
            this.token = resp.data;
            this.showTokenModal = true;
            this.$root.$emit('token_created');
          })
          .catch(error => {
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
      }

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