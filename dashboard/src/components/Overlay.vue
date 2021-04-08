<template>
  <div v-if="isOverlayVisible" class="ui-overlay" @click="close"></div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import { mapState } from 'vuex'
import { AppModule } from "../store/modules/app";

@Component({
  name: 'Overlay'
})
export default class Overlay extends Vue {
  get isOverlayVisible() {
    return AppModule.isOverlayVisible;
  }

  close() {
    this.$store.commit('overlayToggle', false)
  }
}
</script>
