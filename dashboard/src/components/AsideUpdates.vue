<template>
  <div>
    <!-- <aside-updates-item v-for="item in items" :key="item.id" :status="item.status" :icon="item.icon" :ago="item.ago">
      <p>{{ item.text }}</p>
    </aside-updates-item> -->
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import axios from "axios"
import AsideUpdatesItem from "./AsideUpdatesItem.vue"

@Component({
  name: 'AsideUpdates',
  components: { AsideUpdatesItem }
})
export default class AsideUpdates extends Vue {
  items = [];

  mounted() {
    this.getData()
  }

  getData() {
    // axios
    //   .get('/data-sources/updates.json')
    //   .then(r => {
    //     this.items = r.data.data
    //     this.$emit('data-updated')

    //     this.$store.commit('basic', {
    //       key: 'hasUpdates',
    //       value: true
    //     })
    //   })
    //   .catch(err => {
    //     this.$buefy.toast.open({
    //       message: `Error: ${err.message}`,
    //       type: 'is-danger'
    //     })
    //   })
  }
}
</script>
