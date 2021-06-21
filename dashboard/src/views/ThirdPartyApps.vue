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
            <app-authorizations-table
              :authorizations="authorizations"
              :loading="loading"
              v-on:delete-authorization="onDeleteAuthorization($event)"
            ></app-authorizations-table>
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
import AppAuthorizationsTable from "../components/AppAuthorizationsTable.vue";
import {
  deleteAppAuthorization,
  getAppAuthorizations,
} from "../api/app-authorizations";
import { AppAuthorization } from "../api/types";

@Component({
  name: "app-authorizations",

  components: {
    CardComponent,
    AppAuthorizationsTable,
    TitleBar,
  },
})
export default class ThirdPartyApps extends Vue {
  authorizations: AppAuthorization[] = [];
  loading = false;

  get titleStack() {
    return ["Third-Party Apps"];
  }

  mounted() {
    this.loadAuthorizations();
  }

  refresh() {
    this.loadAuthorizations();
  }

  loadAuthorizations() {
    this.loading = true;
    getAppAuthorizations()
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
    deleteAppAuthorization(tokenId)
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
