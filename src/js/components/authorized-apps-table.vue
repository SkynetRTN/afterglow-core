<template>
    <section>
        <b-table
            :data="data"
            :loading="loading"
            striped="true">

            <template slot-scope="props">
                <b-table-column field="name" label="Name">
                    {{ props.row.name }}
                </b-table-column>

                <b-table-column field="options" label="Options">
                    <button class="button is-danger" v-on:click="denyApp(props.row.id)">Revoke Access</button>
                     
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
import { userService } from "../services";

export default {
  data() {
    return {
      data: [],
      loading: false,
    };
  },
  props: ["userId"],
  methods: {
    refresh() {
      this.loadAsyncData();
    },
    loadAsyncData() {
      this.loading = true;
      userService
        .getAuthorizedApps(this.userId)
        .then(({ data }) => {
          this.data = [...data];
          this.loading = false;
        })
        .catch(error => {
          this.data = [];
          this.loading = false;
          throw error;
        });
    },
    denyApp(appId) {
      this.loading = true;
      let fields = ['id', 'type', 'state']
      userService
        .removeAuthorizedApp(this.userId, appId)
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
  }
};
</script>