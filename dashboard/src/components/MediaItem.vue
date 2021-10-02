<template>
  <article v-if="!isDismissed" class="media">
    <figure class="media-left" v-if="item.avatar">
      <p class="image is-64x64">
        <img :src="item.avatar" class="is-rounded">
      </p>
    </figure>
    <div class="media-content">
      <div class="content">
        <p class="media-meta">
          <strong>{{ item.name }}</strong>
          <small v-if="item.login">@{{ item.login }}</small>
          <small class="has-text-grey">{{ item.ago }}</small>
        </p>
        <p>
          {{ item.text }}
        </p>
      </div>
      <nav v-if="hasShareButtons" class="level is-mobile">
        <div class="level-left">
          <a class="level-item">
            <b-icon icon="reply" custom-size="default"/>
          </a>
          <a class="level-item">
            <b-icon icon="twitter-retweet" custom-size="default"/>
          </a>
          <a class="level-item">
            <b-icon icon="heart-outline" custom-size="default"/>
          </a>
        </div>
      </nav>
    </div>
    <div v-if="hasDismiss" class="media-right" @click="dismiss">
      <button class="delete"></button>
    </div>
  </article>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'MediaItem'
})
export default class MediaItem extends Vue {
  @Prop({
    type: Object,
    default: () => {}
  })
  item;

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

  isDismissed = false;

  dismiss() {
    this.isDismissed = true
    this.$buefy.snackbar.open({
      message: 'Dismissed',
      queue: false
    })
  }
}
</script>
