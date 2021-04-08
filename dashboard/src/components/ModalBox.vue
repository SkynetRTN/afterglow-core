<template>
  <b-modal :active.sync="isModalActive" has-modal-card>
    <div class="modal-card">
      <header class="modal-card-head">
        <p class="modal-card-title">Confirm action</p>
      </header>
      <section class="modal-card-body">
        <p>This will permanently delete <b>{{ trashObjectName }}</b></p>
        <p>Action can not be undone.</p>
      </section>
      <footer class="modal-card-foot">
        <button class="button" type="button" @click="cancel">Cancel</button>
        <button class="button is-danger" @click="confirm">Delete</button>
      </footer>
    </div>
  </b-modal>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'ModalBox',

  watch: {
    isActive (newValue) {
      // TODO: FIX
      // this.isModalActive = newValue
    },
    isModalActive (newValue) {
      // TODO: FIX
      // if (!newValue) {
      //   this.cancel()
      // }
    }
  }
})
export default class ModalBox extends Vue {
  @Prop({
    type: Boolean,
    default: false
  })
  isActive;

  @Prop({
    type: String,
    default: null
  })
  trashObjectName;

  isModalActive = false;

  cancel() {
    this.$emit('cancel')
  }

  confirm() {
    this.$emit('confirm')
  }
}
</script>
