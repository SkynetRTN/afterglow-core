<template>
  <div>
    <title-bar :title-stack="titleStack" />
    <section class="section is-main-section">
      <div class="columns is-desktop">
        <div class="column">
          <card-component
            title="Tokens"
            icon="key"
            header-icon="reload"
            v-on:header-icon-click="refresh()"
          >
            <token-table
              :tokens="tokens"
              :loading="loading"
              v-on:delete-token="onDeleteToken($event)"
            ></token-table>
          </card-component>
        </div>

        <div class="column">
          <card-component title="Create New Token" icon="pencil">
            <create-token-form
              v-on:token-created="onTokenCreated($event)"
            ></create-token-form>
          </card-component>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";

import TitleBar from "../components/TitleBar.vue";
import CardComponent from "../components/CardComponent.vue";
import TokenTable from "../components/TokensTable.vue";
import CreateTokenForm from "../components/CreateTokenForm.vue";
import { Token, TokenLtd } from "../api/types";
import { deleteToken, getTokens } from "../api/tokens";

@Component({
  name: "access-tokens",

  components: {
    CardComponent,
    TokenTable,
    CreateTokenForm,
    TitleBar,
  },
})
export default class AccessTokens extends Vue {
  tokens: TokenLtd[] = [];
  loading = false;

  get titleStack() {
    return ["Access Tokens"];
  }

  mounted() {
    this.loadTokens();
  }

  refresh() {
    this.loadTokens();
  }

  loadTokens() {
    this.loading = true;
    getTokens()
      .then(({ data }) => {
        this.tokens = data;
        this.loading = false;
      })
      .catch((error) => {
        this.tokens = [];
        this.loading = false;
        throw error;
      });
  }

  onDeleteToken(tokenId: number) {
    this.loading = true;
    deleteToken(tokenId)
      .then(() => {
        return this.loadTokens();
        this.loading = false;
      })
      .catch((error) => {
        this.tokens = [];
        this.loading = false;
        throw error;
      });
  }

  onTokenCreated(token: Token) {
    this.loadTokens();
  }
}
</script>
