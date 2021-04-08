<template>
  <div>
    <title-bar :title-stack="titleStack" />
    <section class="section is-main-section">
      <div class="columns is-desktop">
        <div class="column">
          <card-component
            title="Application Access"
            icon="key"
            header-icon="reload"
            v-on:header-icon-click="refresh()"
          >
            <oauth-client-authorizations-table
              :authorizations="authorizations"
              :loading="loading"
              v-on:delete-authorization="onDeleteAuthorization($event)"
            ></oauth-client-authorizations-table>
          </card-component>
        </div>

        <div class="column"></div>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";

import TitleBar from "../components/TitleBar.vue";
import CardComponent from "../components/CardComponent.vue";
import OauthClientAuthorizationsTable from "../components/OauthClientAuthorizationsTable.vue";
import {
  deleteOauthClientAuthorization,
  getOauthClientAuthorizations,
} from "../api/oauth-client-authorizations";
import { OauthClientAuthorization } from "../api/types";

@Component({
  name: "oauth-client-authorizations",

  components: {
    CardComponent,
    OauthClientAuthorizationsTable,
    TitleBar,
  },
})
export default class OauthClientAuthorizations extends Vue {
  authorizations: OauthClientAuthorization[] = [];
  loading = false;

  get titleStack() {
    return ["Third-Party Application Access"];
  }

  mounted() {
    this.loadAuthorizations();
  }

  refresh() {
    this.loadAuthorizations();
  }

  loadAuthorizations() {
    this.loading = true;
    getOauthClientAuthorizations()
      .then(({ data }) => {
        this.authorizations = data;
        this.loading = false;
      })
      .catch((error) => {
        this.authorizations = [];
        this.loading = false;
        throw error;
      });
  }

  onDeleteAuthorization(tokenId: number) {
    this.loading = true;
    deleteOauthClientAuthorization(tokenId)
      .then(() => {
        return this.loadAuthorizations();
        this.loading = false;
      })
      .catch((error) => {
        this.authorizations = [];
        this.loading = false;
        throw error;
      });
  }
}
</script>
