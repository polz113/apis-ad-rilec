<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateOURelationsTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('o_u_relations', function (Blueprint $table) {
            $table->id();
            $table->timestamps();
            $table->foreignId('h_r_master_update_id')->constrained()->onDelete('cascade');
            $table->string('child_uid');
            $table->string('parent_uid'); 
            $table->datetime('changed_at')->nullable();
            $table->datetime('valid_from')->nullable();
            $table->datetime('valid_to')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('o_u_relations');
    }
}
