<template>
  <section class="section hero is-fullheight is-error-section" style="background: #0a121f">
    <div class="hero-body">
      <div class="container">
        <router-view/>
      </div>
    </div>
    <div class="hero-foot has-text-centered">
      <div class="logo"></div>
    </div>
  </section>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import { AppModule } from '../store/modules/app'

@Component({
  name: 'FullPage'
})
export default class FullPage extends Vue {
  created() {
    this.$store.dispatch('SetFullPageMode', true)
    this.$store.dispatch('ToggleRightSideBar', false)
  }

  beforeDestroy() {
    this.$store.dispatch('SetFullPageMode', false)
  }
}
</script>
