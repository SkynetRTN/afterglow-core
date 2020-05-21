<template>
    <section>
        <b-table
            :data="data"
            :loading="loading"
            striped="true">

            <template slot-scope="props">
                <b-table-column field="note" label="Note">
                    {{ props.row.note }}
                </b-table-column>

                <b-table-column field="options" label="Options" width="250">
                    <button class="button is-danger" v-on:click="deleteToken(props.row.id)">Delete Token</button>
                     
                </b-table-column>

            </template>
            <template slot="empty">
                <section class="section">
                    <div class="content has-text-grey has-text-centered">
                        <p>
                            <i class="fa fa-frown-open fa-3x is-large"></i>
                        </p>
                        <p>Nothing here.</p>
                    </div>
                </section>
            </template>
        </b-table>
    </section>
</template>

<script>
import { coreService } from "../services";

export default {
  data() {
    return {
      data: [],
      loading: false,
    };
  },
  methods: {
    refresh() {
      this.loadAsyncData();
    },
    loadAsyncData() {
      this.loading = true;
      coreService
        .getTokens()
        .then(({ data }) => {
          this.data = [...data.items];
          this.loading = false;
        })
        .catch(error => {
          this.data = [];
          this.loading = false;
          throw error;
        });
    },
    deleteToken(tokenId) {
      this.loading = true;
      coreService
        .deleteToken(tokenId)
        .then(() => {
          return this.loadAsyncData();
        })
        .catch(error => {
          this.data = [];
          this.loading = false;
          throw error;
        });
    }
  },
  filters: {
    /**
     * Filter to truncate string, accepts a length parameter
     */
    truncate(value, length) {
      return value.length > length ? value.substr(0, length) + "..." : value;
    }
  },
  mounted() {
    this.loadAsyncData();
  },
};
</script>