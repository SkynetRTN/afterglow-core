<template>
  <article class="media">
    <div class="media-content">
      <div class="content">
        <slot/>
      </div>
      <nav class="level is-mobile">
        <div class="level-left">
          <div class="level-item">
            <span v-if="icon" class="tag is-small" :class="status">
              <b-icon :icon="icon" size="is-small"/>
            </span>
          </div>
          <div v-if="ago" class="level-item">
            <small>{{ ago }}</small>
          </div>
        </div>
      </nav>
    </div>
  </article>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'AsideUpdatesItem'
})
export default class AsideUpdatesItem extends Vue {
  @Prop({
    type: String,
    default: null
  })
  icon;

  @Prop({
    type: String,
    default: 'is-info'
  })
  status;

  @Prop({
    type: String,
    default: null
  })
  ago;
}
</script>
