<template>
  <div v-if="!isDismissed" class="notification">
    <div class="level">
      <div class="level-left">
        <div class="level-item">
          <slot/>
        </div>
      </div>
      <div class="level-right">
        <button type="button" class="button is-small is-white" @click="dismiss">Dismiss</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
@Component({
  name: 'Notification'
})
export default class Notification extends Vue {
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
