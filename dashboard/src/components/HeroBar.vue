<template>
  <section class="hero is-hero-bar">
    <div class="hero-body">
      <div class="level">
        <div class="level-left">
          <div class="level-item">
            <h1 class="title">
              <slot/>
            </h1>
          </div>
        </div>
        <div v-show="hasRightVisible" class="level-right">
          <div class="level-item">
            <slot name="right"/>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'HeroBar'
})
export default class HeroBar extends Vue {
  @Prop({
    type: Boolean,
    default: true
  })
  hasRightVisible;
}
</script>
