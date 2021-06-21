<template>
  <card-component :title="title" :icon="icon" :is-scrollable="true" :has-button-slot="true" :has-footer-slot="true" @ps-ready="psReady">
    <refresh-button slot="button" :is-loading="isLoading" @button-click="delayedFetch"/>
    <card-toolbar slot="toolbar" class="is-upper" :class="(status.toolbarClass) ? status.toolbarClass : null">
      <div v-if="status.text" slot="left">{{ status.text }}</div>
      <span v-if="(status.label || status.labelIcon)" class="tag" :class="status.labelClass" slot="right">
        <b-icon v-if="status.labelIcon" :icon="status.labelIcon" custom-size="default"/>
        <span v-if="status.label">{{ status.label }}</span>
      </span>
    </card-toolbar>

    <div class="media-list">
      <b-loading :is-full-page="false" :active="isLoading"/>
      <media-item v-for="item in items" :key="item.id" :item="item" :has-share-buttons="hasShareButtons" :has-dismiss="hasDismiss"/>
    </div>

    <a class="card-footer-item" slot="footer" @click.prevent="delayedFetch">
      <b-icon icon="autorenew" custom-size="default"/>
      <span>Load more</span>
    </a>
  </card-component>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import axios from 'axios'
import CardComponent from './CardComponent.vue'
import CardToolbar from './CardToolbar.vue'
import MediaItem from '@/components/MediaItem.vue'
import RefreshButton from './RefreshButton.vue'
import PerfectScrollbar from "perfect-scrollbar";
@Component({
  name: 'CardScrollable',
  components: { RefreshButton, MediaItem, CardToolbar, CardComponent }
})
export default class CardScrollable extends Vue {
  private ps: PerfectScrollbar;

  @Prop({
    type: String,
    default: null
  })
  title;

  @Prop({
    type: String,
    default: null
  })
  icon;

  @Prop({
    type: String,
    default: null
  })
  dataUrl;

  @Prop({
    type: Boolean,
    default: false
  })
  hasShareButtons;

  @Prop({
    type: Boolean,
    default: false
  })
  hasDismiss;

  isLoading = false;
  items = [];
  status = {};

  mounted() {
    this.fetchData()
  }

  psReady(ps) {
    this.ps = ps
  }

  delayedFetch() {
    this.isLoading = true

    this.items = []

    this.status = {
      text: 'Fetching data...',
      labelClass: 'is-info',
      labelIcon: 'shuffle-variant'
    }

    setTimeout(() => {
      this.fetchData()
    }, 500)
  }

  fetchData() {
    this.isLoading = true

    this.items = []

    this.status = {
      text: 'Fetching data...',
      labelClass: 'is-info',
      labelIcon: 'shuffle-variant'
    }

    axios
      .get(this.dataUrl)
      .then(r => {
        this.isLoading = false

        if (r.data) {
          if (r.data.data) {
            this.items = r.data.data
          }
          if (r.data.status) {
            this.status = r.data.status
          }
        }

        this.$nextTick(() => {
          if (this.ps) {
            this.ps.update()
          }
        })
      })
      .catch(e => {
        this.isLoading = false
        this.$buefy.toast.open({
          message: `Error: ${e.message}`,
          type: 'is-danger'
        })
      })
  }
}
</script>
