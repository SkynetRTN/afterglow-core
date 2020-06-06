<template>
    <section>
        <b-table
            :data="data"
            :loading="loading"
            striped="true"
            :opened-detailed="defaultOpenedDetails"
            detailed
            detail-key="id"
            @details-open="(row, index) => $buefy.toast.open(`Expanded ${row.name}`)"
            :show-detail-icon="showDetailIcon">

            <template slot-scope="props">
                <b-table-column field="id" label="ID">
                    {{ props.row.id }}
                </b-table-column>

                <b-table-column field="type" label="Type">
                        {{ props.row.type }}
                </b-table-column>

                <b-table-column field="state" label="State">
                        
                     
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
      total: null,
      loading: false,
      sortField: "id",
      sortOrder: "desc",
      defaultSortOrder: "desc",
      page: 1,
      perPage: 20,
      defaultOpenedDetails: [],
      showDetailIcon: true
    };
  },
  methods: {
    /*
        * Load async data
        */
    loadAsyncData() {
      this.loading = true;
      let fields = ['id', 'type', 'state']
      coreService
        .getJobs(fields, this.page, this.perPage)
        .then(({ data }) => {
          this.data = [...data.items];
          if(data.length == this.perPage) {
              this.total = (this.page+1)*this.perPage;
          }
          else {
              this.total = (this.page-1)*this.perPage + data.length;
          }
          this.loading = false;
        })
        .catch(error => {
          this.data = [];
          this.total = 0;
          this.loading = false;
          throw error;
        });
    },
    /*
        * Handle page-change event
        */
    onPageChange(page) {
      this.page = page;
      this.loadAsyncData();
    },
    /*
        * Handle sort event
        */
    onSort(field, order) {
      this.sortField = field;
      this.sortOrder = order;
      this.loadAsyncData();
    },
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