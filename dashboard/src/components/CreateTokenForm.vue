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
          <input
            id="note"
            name="note"
            v-model="note"
            type="text"
            value
            class="input"
            placeholder="What’s this token for?"
          />
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
          >
            Create
          </button>
        </div>
      </div>
    </form>
    <b-modal
      :active.sync="showTokenModal"
      has-modal-card
      trap-focus
      :destroy-on-hide="true"
      aria-role="dialog"
      aria-modal
    >
      <token-modal :token="token"></token-modal>
    </b-modal>
  </section>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from "vue-property-decorator";
import CardComponent from "./CardComponent.vue";
import TokenModal from "./TokenModal.vue"
import { appConfig } from "../config";
import { UserModule } from "../store/modules/user";
import { AppModule } from "../store/modules/app";
import { getServerStatus } from "../api/server-status";

import axios from "axios";
import { Token } from "../api/types";
import { createToken } from "../api/tokens";

@Component({
  name: "create-token-form",
  components: { TokenModal },
})
export default class CreateTokenForm extends Vue {
  @Prop({ default: '' })
  cancelUrl!: string

  note: string = null;
  loading = false;
  errors: string[] = [];
  token: Token = null;
  showTokenModal = false;

  get submitDisabled() {
      return this.loading;
    }

  formSubmit(e) {
      e.preventDefault();

      this.errors = [];

      if (!this.note) {
        this.errors.push("A note is required.");
      }

      if (this.errors.length == 0) {
        this.loading = true;
        createToken({
            note: this.note,
          })
          .then((resp) => {
            this.note = "";
            this.token = resp.data;
            this.showTokenModal = true;
            this.$emit("token-created", this.token);
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
                      r.data[field].forEach((e) => this.errors.push(e));
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
}


</script>
