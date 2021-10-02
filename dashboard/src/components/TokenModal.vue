<template>
  <div class="modal-card" style="width: auto">
    <section class="modal-card-body">
      <div class="container">
        <div class="content">
          <p>
            A personal access token was successfully created. You will only be able to view the
            token once so be sure to copy it now before closing this dialog window.
          </p>
          <div class="field has-addons">
            <div class="control is-expanded">
              <input
                id="access_token"
                class="input"
                type="text"
                :value="token.accessToken"
                readonly
              />
            </div>
            <div class="control">
              <button
                class="button is-info"
                data-clipboard-target="#access_token"
                alt="Copy to clipboard"
                v-clipboard:copy="token.accessToken"
              >
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
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from "vue-property-decorator";
import { Token } from "../api/types";

@Component({
  name: "token-modal",
})
export default class TokenModal extends Vue {
  @Prop({ default: null })
  token!: Token;
}
</script>
